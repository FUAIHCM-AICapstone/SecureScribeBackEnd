from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from app.constants.messages import MessageConstants
from app.core.azure_oauth_utils import (
    azure_oauth_utils_manager,
    check_azure_granted_scopes,
    process_azure_token,
)
from app.core.config import settings
from app.db import get_db
from app.models.user import User
from app.schemas.auth import (
    RefreshTokenRequest,
)
from app.schemas.common import ApiResponse
from app.schemas.user import UserUpdate
from app.services.auth import azure_login
from app.services.user import update_user
from app.utils.auth import (
    create_access_token,
    get_current_user,
    verify_token,
)
from app.utils.logging import logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["Auth"])
security = HTTPBearer()


@router.post("/auth/refresh", response_model=ApiResponse[dict])
def refresh_token_endpoint(request: RefreshTokenRequest):
    refresh_token = request.refresh_token

    try:
        payload = verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MessageConstants.INVALID_CREDENTIALS)

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MessageConstants.INVALID_CREDENTIALS)

        access_token = create_access_token({"sub": user_id})

        return ApiResponse(
            success=True,
            message=MessageConstants.OPERATION_SUCCESSFUL,
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            },
        )
    except Exception:
        raise


@router.get("/me", response_model=ApiResponse[dict])
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return ApiResponse(
        success=True,
        message=MessageConstants.USER_RETRIEVED_SUCCESS,
        data={
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name,
            "avatar_url": current_user.avatar_url,
            "bio": current_user.bio,
            "position": current_user.position,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at,
        },
    )


@router.put("/me", response_model=ApiResponse[dict])
def update_current_user_info(
    updates: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    update_data = updates.model_dump(exclude_unset=True)
    updated_user = update_user(db, current_user.id, **update_data)
    return ApiResponse(
        success=True,
        message=MessageConstants.USER_UPDATED_SUCCESS,
        data={
            "id": updated_user.id,
            "email": updated_user.email,
            "name": updated_user.name,
            "avatar_url": updated_user.avatar_url,
            "bio": updated_user.bio,
            "position": updated_user.position,
            "created_at": updated_user.created_at,
            "updated_at": updated_user.updated_at,
        },
    )


@router.get("/auth/azure/login", response_class=RedirectResponse)
async def azure_login(
    request: Request,
    scopes: Optional[str] = None,
    login_hint: Optional[str] = None,
) -> RedirectResponse:
    """Initiate Azure AD OAuth login flow

    This endpoint directly redirects to Azure AD for authentication.

    Query Parameters:
        scopes (str, optional): Comma-separated list of scopes to request
        login_hint (str, optional): Email hint for the Azure AD login page

    Returns:
        RedirectResponse: Direct redirect to Azure AD login page

    Example:
        GET /api/v1/auth/azure/login?login_hint=user@example.com
    """
    try:
        logger.info(f"[AZURE LOGIN] Azure login initiated with hint: {login_hint}")

        # Parse scopes if provided
        scope_list = scopes.split(",") if scopes else None

        # Generate authorization URL
        auth_url = azure_oauth_utils_manager.get_auth_url(scope_list, login_hint)

        logger.info("[AZURE LOGIN] Redirecting to Azure AD authorization URL")

        # Return direct redirect to Azure AD
        return RedirectResponse(url=auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    except Exception as e:
        logger.error(f"[AZURE LOGIN] Error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to initiate login: {str(e)}")


@router.get("/auth/azure/callback")
async def azure_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    """Handle Azure AD OAuth callback and redirect to frontend with tokens

    This endpoint is called by Azure AD after the user logs in.
    It exchanges the authorization code for tokens and creates/updates the user.

    Query Parameters:
        code: Authorization code from Azure AD (required)
        state: State parameter for CSRF protection (optional)
        error: Error code if authentication failed (optional)
        error_description: Error description (optional)

    Returns:
        HTMLResponse: HTML page with embedded tokens for parent window communication

    Example:
        Azure AD redirects to: /api/v1/auth/azure/callback?code=M.R3_BAY...&state=xyz
    """
    try:
        logger.info("[AZURE CALLBACK] Azure AD callback received")

        # Check for errors from Azure AD
        error = request.query_params.get("error")
        if error:
            error_description = request.query_params.get("error_description", "Unknown error")
            error_message = f"Azure AD error: {error} - {error_description}"
            logger.error(f"[AZURE CALLBACK] {error_message}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_message)

        # Get authorization code
        code = request.query_params.get("code")
        if not code:
            logger.error("[AZURE CALLBACK] Missing authorization code")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing authorization code")

        logger.info("[AZURE CALLBACK] Authorization code received, exchanging for tokens")

        # Exchange code for tokens
        token_result = azure_oauth_utils_manager.acquire_token_by_authorization_code(code)
        logger.info("[AZURE CALLBACK] Token retrieved from Azure AD")

        # Get user info using access token
        access_token = token_result.get("access_token")
        if not access_token:
            logger.error("[AZURE CALLBACK] Failed to get access token")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to get access token")

        user_info = azure_oauth_utils_manager.get_user_info(access_token)
        logger.info(f"[AZURE CALLBACK] User info retrieved: {user_info.get('mail', 'No email')}")

        # Combine token and user info
        token_data = {**token_result, "user_info": user_info}

        # Process and validate token data
        token_data = process_azure_token(token_data)
        logger.info("[AZURE CALLBACK] Token processed successfully")

        user_info_dict = token_data.get("user_info", {})
        logger.info(f"[AZURE CALLBACK] User info extracted: {user_info_dict.get('email', 'No email')}")

        # Check granted scopes
        granted_scopes = check_azure_granted_scopes(token_data)

        # Login user with our API
        logger.info(f"[AZURE CALLBACK] Logging in user: {user_info_dict.get('email')}")
        api_result = azure_login(db, code)

        logger.info("[AZURE CALLBACK] User data after login retrieved")

        # Generate the success page with tokens that will send postMessage to parent window
        logger.info("[AZURE CALLBACK] Generating success page with tokens")

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Successful</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: 'Roboto', -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 12px;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
                    text-align: center;
                    max-width: 500px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 20px;
                    margin: -40px -40px 20px -40px;
                    border-radius: 12px 12px 0 0;
                }}
                .header h1 {{
                    color: white;
                    margin: 0;
                    font-size: 24px;
                }}
                .spinner {{
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #667eea;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    animation: spin 1s linear infinite;
                    margin: 20px auto;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
                .user-info {{
                    background: #f5f5f5;
                    padding: 15px;
                    border-radius: 6px;
                    margin: 20px 0;
                    text-align: left;
                    font-size: 14px;
                }}
                .user-info strong {{
                    display: block;
                    margin-bottom: 5px;
                    color: #333;
                }}
                p {{
                    color: #666;
                    margin: 10px 0;
                }}
            </style>
            <script>
                window.onload = function() {{
                    const authData = {{
                        type: 'AZURE_AUTH_SUCCESS',
                        access_token: '{api_result["token"]["access_token"]}',
                        refresh_token: '{api_result["token"]["refresh_token"]}',
                        token_type: '{api_result["token"]["token_type"]}',
                        expires_in: {api_result["token"]["expires_in"]},
                        user: {{
                            id: '{api_result["user"]["id"]}',
                            email: '{api_result["user"]["email"]}',
                            name: '{api_result["user"]["name"]}'
                        }},
                        timestamp: Date.now()
                    }};
                    
                    // Store tokens in localStorage
                    localStorage.setItem('auth_tokens', JSON.stringify({{
                        access_token: authData.access_token,
                        refresh_token: authData.refresh_token,
                        token_type: authData.token_type,
                        expires_in: authData.expires_in
                    }}));
                    
                    // Store user info
                    localStorage.setItem('user_info', JSON.stringify(authData.user));
                    
                    // Send message to parent window if opened in iframe/popup
                    if (window.opener) {{
                        window.opener.postMessage(authData, '*');
                        setTimeout(function() {{ window.close(); }}, 2000);
                    }} else if (window.parent !== window) {{
                        window.parent.postMessage(authData, '*');
                    }} else {{
                        // No parent window, redirect to dashboard
                        setTimeout(function() {{
                            window.location.href = '/dashboard';
                        }}, 2000);
                    }}
                }};
            </script>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✓ Authentication Successful</h1>
                </div>
                <div class="spinner"></div>
                <div class="user-info">
                    <strong>Email:</strong> {api_result["user"]["email"]}<br>
                    <strong>Name:</strong> {api_result["user"]["name"]}
                </div>
                <p>Redirecting you to the application...</p>
            </div>
        </body>
        </html>
        """

        return HTMLResponse(content=html_content)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AZURE CALLBACK] Error: {str(e)}", exc_info=True)

        # Return error HTML that will communicate with parent window
        error_message = str(e)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Failed</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: 'Roboto', -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
                    flex-direction: column;
                    text-align: center;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
                }}
                .header {{
                    background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
                    padding: 20px;
                    text-align: center;
                }}
                .header h1 {{
                    color: #ffffff;
                    margin: 0;
                    font-size: 24px;
                }}
                .content {{
                    padding: 30px;
                }}
                .error-message {{
                    background: #ffebee;
                    border-left: 4px solid #f44336;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 4px;
                    text-align: left;
                    font-size: 14px;
                    color: #c62828;
                    word-break: break-word;
                }}
                p {{
                    color: #666;
                    margin: 10px 0;
                }}
            </style>
            <script>
                window.onload = function() {{
                    if (window.opener) {{
                        window.opener.postMessage({{
                            type: 'AZURE_AUTH_ERROR',
                            error: '{error_message}',
                            timestamp: Date.now()
                        }}, '*');
                        setTimeout(function() {{ window.close(); }}, 3000);
                    }} else if (window.parent !== window) {{
                        window.parent.postMessage({{
                            type: 'AZURE_AUTH_ERROR',
                            error: '{error_message}',
                            timestamp: Date.now()
                        }}, '*');
                    }}
                }};
            </script>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✗ Authentication Failed</h1>
                </div>
                <div class="content">
                    <div class="error-message">
                        <strong>Error:</strong> {error_message}
                    </div>
                    <p>This window will close automatically in 3 seconds...</p>
                </div>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
