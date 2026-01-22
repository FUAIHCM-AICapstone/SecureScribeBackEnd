"""Azure AD OAuth Utilities using MSAL

This module provides utilities for Azure AD OAuth authentication using MSAL Python library.
It handles authorization flow, token exchange, user info retrieval, and scope validation.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import msal
import requests

from app.core.config import settings
from app.utils.logging import logger

logger_instance = logging.getLogger(__name__)


class AzureOAuthUtilsManager:
    """Manages Azure AD OAuth authentication using MSAL"""

    def __init__(self):
        self.client_id = settings.AZURE_CLIENT_ID
        self.client_secret = settings.AZURE_CLIENT_SECRET
        self.tenant_id = settings.AZURE_TENANT_ID
        self.redirect_uri = settings.AZURE_REDIRECT_URI
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        # Only get user profile when login
        self.default_scopes = [settings.AZURE_SCOPE]

        # Proxy configuration - support both custom and standard env vars
        self.proxies = self._configure_proxies()

        # Initialize MSAL Confidential Client Application with proxy-configured http_client
        session = requests.Session()
        session.proxies.update(self.proxies)

        self.app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=self.authority,
            http_client=session,
        )

    def _configure_proxies(self) -> Dict[str, str]:
        """Configure proxies with support for custom and standard environment variables.

        Priority:
        1. Custom PROXY_HOST and PROXY_PORT environment variables
        2. Standard HTTP_PROXY and HTTPS_PROXY environment variables
        3. Empty dict if no proxy is configured
        """
        proxies = {}

        # Check for custom proxy configuration first
        proxy_host = os.getenv("PROXY_HOST")
        proxy_port = os.getenv("PROXY_PORT")

        if proxy_host and proxy_port:
            try:
                proxy_port = int(proxy_port)
                proxy_url = f"http://{proxy_host}:{proxy_port}"
                proxies = {"http": proxy_url, "https": proxy_url}
                logger.info(f"Using custom proxy configuration: {proxy_host}:{proxy_port}")
                # Also set standard env vars for Azure SDK compatibility
                os.environ["HTTP_PROXY"] = proxy_url
                os.environ["HTTPS_PROXY"] = proxy_url
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid custom proxy configuration: {e}")
        else:
            # Fall back to standard HTTP_PROXY and HTTPS_PROXY env vars if custom not set
            http_proxy = os.getenv("HTTP_PROXY")
            https_proxy = os.getenv("HTTPS_PROXY")
            if http_proxy:
                proxies["http"] = http_proxy
            if https_proxy:
                proxies["https"] = https_proxy
            if proxies:
                logger.info(f"Using standard proxy configuration: {proxies}")

        return proxies

    def get_auth_url(self, scopes: Optional[List[str]] = None, login_hint: Optional[str] = None) -> str:
        """Generate Azure AD authorization URL

        Args:
            scopes: List of scopes to request (defaults to User.Read)
            login_hint: Pre-fill the username field

        Returns:
            Authorization URL to redirect user to
        """
        scopes = scopes or self.default_scopes

        auth_url = self.app.get_authorization_request_url(
            scopes=scopes,
            redirect_uri=self.redirect_uri,
            login_hint=login_hint,
        )

        return auth_url

    def acquire_token_by_authorization_code(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens

        Args:
            code: Authorization code from Azure AD

        Returns:
            Token response containing access_token, refresh_token, etc.

        Raises:
            Exception: If token acquisition fails
        """
        result = self.app.acquire_token_by_authorization_code(
            code=code,
            scopes=self.default_scopes,
            redirect_uri=self.redirect_uri,
        )

        if "error" in result:
            error_msg = f"Token acquisition failed: {result.get('error_description', result['error'])}"
            logger.error(error_msg)
            raise Exception(error_msg)

        return result

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Microsoft Graph API

        Args:
            access_token: Access token from Azure AD

        Returns:
            User information dictionary containing email, name, photo, etc.

        Raises:
            Exception: If user info retrieval fails
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # Get user profile from Microsoft Graph
        try:
            response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers, proxies=self.proxies, timeout=30)

            if response.status_code != 200:
                error_msg = f"Failed to get user info: {response.text}"
                logger.error(error_msg)
                raise Exception(f"Failed to get user info: {response.status_code}")

            user_info = response.json()

            # Get user photo if available
            try:
                photo_response = requests.get("https://graph.microsoft.com/v1.0/me/photo/$value", headers=headers, proxies=self.proxies, timeout=30)
                if photo_response.status_code == 200:
                    # Convert photo to base64
                    import base64

                    user_info["picture"] = f"data:image/jpeg;base64,{base64.b64encode(photo_response.content).decode()}"
            except Exception as e:
                logger.warning(f"Could not fetch user photo: {e}")

            return user_info

        except requests.RequestException as e:
            error_msg = f"Request failed when getting user info: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)


# Global instance
azure_oauth_utils_manager = AzureOAuthUtilsManager()


def process_azure_token(token_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process and validate Azure AD token data

    Args:
        token_data: Token data from Azure AD

    Returns:
        Processed token data with normalized user information

    Raises:
        Exception: If validation fails
    """
    if not token_data:
        raise Exception("Invalid token data")

    # Extract user info
    user_info = token_data.get("user_info", {})
    if not user_info:
        raise Exception("Missing user information")

    # Validate required fields
    email = user_info.get("email") or user_info.get("mail") or user_info.get("userPrincipalName")
    if not email:
        raise Exception("Missing email address")

    # Normalize user info
    processed_user_info = {
        "email": email,
        "name": user_info.get("displayName", ""),
        "given_name": user_info.get("givenName", ""),
        "family_name": user_info.get("surname", ""),
        "picture": user_info.get("picture"),
        "oid": user_info.get("id", ""),  # Object ID
        "tid": user_info.get("tenantId", ""),  # Tenant ID
        "upn": user_info.get("userPrincipalName", ""),
        "preferred_username": user_info.get("userPrincipalName", ""),
    }

    # Update token data with processed user info
    token_data["user_info"] = processed_user_info

    return token_data


def check_azure_granted_scopes(token_data: Dict[str, Any]) -> Dict[str, bool]:
    """Check which Azure AD scopes were granted and map to features

    Args:
        token_data: Token data from Azure AD

    Returns:
        Dictionary mapping feature names to boolean values indicating granted access
    """
    granted_scopes = token_data.get("scope", "").split() if token_data.get("scope") else []

    features = {
        "calendar_access": False,
        "email_access": False,
        "profile_access": False,
        "contacts_access": False,
    }

    # Map scopes to features
    scope_mapping = {
        "Calendars.Read": "calendar_access",
        "Calendars.ReadWrite": "calendar_access",
        "Mail.Read": "email_access",
        "Mail.ReadWrite": "email_access",
        "User.Read": "profile_access",
        "Contacts.Read": "contacts_access",
        "Contacts.ReadWrite": "contacts_access",
    }

    for scope in granted_scopes:
        if scope in scope_mapping:
            features[scope_mapping[scope]] = True

    return features
