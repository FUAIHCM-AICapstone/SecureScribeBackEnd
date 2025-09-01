from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import api_router
from app.core.config import settings
from app.core.firebase import initialize_firebase
from app.db import get_db
from app.utils.auth import get_current_user_from_token


def custom_generate_unique_id(route: APIRoute) -> str:
    """
    Custom function to generate unique operation IDs for OpenAPI schema.
    This creates cleaner method names for generated client code.
    """
    if route.tags:
        # Use first tag + operation name for better organization
        return f"{route.tags[0]}_{route.name}"
    return route.name


def custom_openapi():
    """
    Custom OpenAPI schema generator with additional metadata and extensions.
    """
    if app.openapi_schema:
        return app.openapi_schema

    # Generate base OpenAPI schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add custom extensions
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png",
        "altText": "SecureScribe API Logo",
    }

    # Add custom servers for different environments
    openapi_schema["servers"] = [
        {"url": "http://localhost:8000", "description": "Development server"},
        {"url": "https://api.securescribe.com", "description": "Production server"},
    ]

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT Authorization header using the Bearer scheme.",
        }
    }

    # Apply security globally
    openapi_schema["security"] = [{"BearerAuth": []}]

    # Cache the schema
    app.openapi_schema = openapi_schema
    return openapi_schema


app = FastAPI(
    title="SecureScribeBE",
    version="1.0.0",
    contact={
        "name": "SecureScribe Team",
        "email": "support@securescribe.com",
    },
    license_info={
        "name": "MIT",
    },
    # Custom operation ID generation for better client code
    generate_unique_id_function=custom_generate_unique_id,
)

# Override the default OpenAPI schema generator
app.openapi = custom_openapi

# Configure CORS for cross-origin requests with Authorization headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        [str(origin) for origin in settings.BACKEND_CORS_ORIGINS]
        if settings.BACKEND_CORS_ORIGINS
        else ["*"]
    ),
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers including Authorization
)

# Initialize Firebase SDK
initialize_firebase()

app.include_router(api_router)


@app.get("/test-auth")
def test_auth_endpoint(request: Request) -> Dict[str, Any]:
    auth_header = request.headers.get("authorization", "")

    if not auth_header:
        return {
            "message": "No Authorization header found",
            "usage": "Add 'Authorization: Bearer <token>' to your request headers",
            "example": "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        }

    if not auth_header.lower().startswith("bearer "):
        return {
            "message": "Invalid Authorization header format",
            "usage": "Header must start with 'Bearer '",
            "example": "Authorization: Bearer <your_jwt_token>",
        }

    token = (
        auth_header[len("bearer ") :]
        if auth_header.lower().startswith("bearer ")
        else auth_header[len("Bearer ") :]
    )
    user_id = get_current_user_from_token(token)

    if not user_id:
        return {
            "message": "Invalid or expired token",
            "token_valid": False,
            "user_id": None,
        }

    return {
        "message": "Token validated successfully",
        "token_valid": True,
        "user_id": user_id,
        "token_preview": token[:20] + "..." if len(token) > 20 else token,
    }


@app.get("/health")
def health(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Health check endpoint that tests database connection
    """
    try:
        # Test database connection with a simple query
        db.query(text("SELECT 1"))
        db.commit()

        return {
            "status": "healthy",
            "database": "connected",
            "server": settings.POSTGRES_SERVER,
            "database_name": settings.POSTGRES_DB,
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "server": settings.POSTGRES_SERVER,
                "database_name": settings.POSTGRES_DB,
            },
        )
