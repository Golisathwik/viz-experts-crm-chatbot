"""
Zoho OAuth Service
------------------
Handles employee-specific Zoho OAuth authentication.

Flow:

1. Employee provides Client ID + Client Secret.
2. Backend stores them encrypted.
3. Backend creates OAuth state + PKCE values.
4. Employee is redirected to Zoho.
5. Zoho redirects back with an authorization code.
6. Backend exchanges the code for access/refresh tokens.
7. Tokens are stored encrypted.
"""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from new_backend.config.settings import settings
from new_backend.repositories.zoho_oauth_repository import (
    ZohoOAuthRepository,
)


ZOHO_SCOPE = ",".join([
    "ZohoCRM.modules.leads.READ",
    "ZohoCRM.modules.leads.CREATE",
    "ZohoCRM.modules.leads.UPDATE",
    "ZohoCRM.modules.leads.DELETE",

    "ZohoCRM.modules.contacts.READ",
    "ZohoCRM.modules.contacts.CREATE",
    "ZohoCRM.modules.contacts.UPDATE",
    "ZohoCRM.modules.contacts.DELETE",

    "ZohoCRM.modules.accounts.READ",
    "ZohoCRM.modules.accounts.CREATE",
    "ZohoCRM.modules.accounts.UPDATE",
    "ZohoCRM.modules.accounts.DELETE",

    "ZohoCRM.modules.deals.READ",
    "ZohoCRM.modules.deals.CREATE",
    "ZohoCRM.modules.deals.UPDATE",
    "ZohoCRM.modules.deals.DELETE",
])


class ZohoOAuthService:

    @staticmethod
    def _create_pkce_pair():

        code_verifier = secrets.token_urlsafe(64)

        digest = hashlib.sha256(
            code_verifier.encode("utf-8")
        ).digest()

        code_challenge = (
            base64.urlsafe_b64encode(digest)
            .decode("utf-8")
            .rstrip("=")
        )

        return code_verifier, code_challenge

    @staticmethod
    def create_authorization_url(
        user_id: int,
        client_id: str,
        client_secret: str,
    ):

        client_id = client_id.strip()
        client_secret = client_secret.strip()

        if not client_id:
            raise ValueError(
                "Zoho Client ID is required."
            )

        if not client_secret:
            raise ValueError(
                "Zoho Client Secret is required."
            )

        # Save this employee's OAuth application credentials.
        ZohoOAuthRepository.save_connection(
            user_id=user_id,
            client_id=client_id,
            client_secret=client_secret,
        )

        # CSRF protection.
        state = secrets.token_urlsafe(32)

        # PKCE protection.
        code_verifier, code_challenge = (
            ZohoOAuthService._create_pkce_pair()
        )

        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(minutes=10)
        ).isoformat()

        ZohoOAuthRepository.save_oauth_state(
            state=state,
            user_id=user_id,
            code_verifier=code_verifier,
            expires_at=expires_at,
        )

        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": settings.ZOHO_REDIRECT_URI,
            "scope": ZOHO_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        authorization_url = (
            f"{settings.ZOHO_ACCOUNTS_URL}/oauth/v2/auth?"
            f"{urlencode(params)}"
        )

        return authorization_url

    @staticmethod
    async def exchange_code(
        state: str,
        code: str,
    ):

        oauth_state = (
            ZohoOAuthRepository.get_oauth_state(state)
        )

        if not oauth_state:
            raise ValueError(
                "Invalid or expired Zoho authorization state."
            )

        # Check expiry.
        expires_at = datetime.fromisoformat(
            oauth_state["expires_at"]
        )

        if (
            expires_at.tzinfo is None
        ):
            expires_at = expires_at.replace(
                tzinfo=timezone.utc
            )

        if datetime.now(timezone.utc) > expires_at:
            ZohoOAuthRepository.delete_oauth_state(
                state
            )

            raise ValueError(
                "Zoho authorization request expired. "
                "Please connect again."
            )

        user_id = oauth_state["user_id"]

        connection = (
            ZohoOAuthRepository.get_connection(user_id)
        )

        if not connection:
            raise ValueError(
                "Zoho connection credentials were not found."
            )

        data = {
            "grant_type": "authorization_code",
            "client_id": connection["client_id"],
            "client_secret": connection["client_secret"],
            "redirect_uri": settings.ZOHO_REDIRECT_URI,
            "code": code,
            "code_verifier": oauth_state["code_verifier"],
        }

        async with httpx.AsyncClient(
            timeout=20.0,
            proxy="http://proxy.server:3128",
        ) as client:

            response = await client.post(
                f"{settings.ZOHO_ACCOUNTS_URL}/oauth/v2/token",
                data=data,
            )

        if response.status_code != 200:
            raise ValueError(
                f"Zoho token exchange failed: "
                f"{response.text}"
            )

        result = response.json()

        access_token = result.get(
            "access_token"
        )

        refresh_token = result.get(
            "refresh_token"
        )

        api_domain = result.get(
            "api_domain"
        )

        if not access_token:
            raise ValueError(
                "Zoho did not return an access token."
            )

        # Usually 3600 seconds.
        expires_in = int(
            result.get("expires_in", 3600)
        )

        token_expires_at = (
            datetime.now(timezone.utc)
            + timedelta(seconds=expires_in)
        ).isoformat()

        ZohoOAuthRepository.update_tokens(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            api_domain=api_domain,
            token_expires_at=token_expires_at,
        )

        # OAuth state is one-time-use.
        ZohoOAuthRepository.delete_oauth_state(
            state
        )

        return {
            "user_id": user_id,
            "api_domain": api_domain,
            "expires_in": expires_in,
        }

    @staticmethod
    def get_connection_status(
        user_id: int,
    ):

        connection = (
            ZohoOAuthRepository.get_connection(
                user_id
            )
        )

        if not connection:
            return {
                "connected": False
            }

        return {
            "connected": bool(
                connection.get("refresh_token")
            ),
            "api_domain": connection.get(
                "api_domain"
            ),
            "connected_at": connection.get(
                "connected_at"
            ),
        }

    @staticmethod
    def disconnect(
        user_id: int,
    ):

        connection = (
            ZohoOAuthRepository.get_connection(
                user_id
            )
        )

        if not connection:
            return

        # We only remove our stored authorization.
        # Actual Zoho token revocation can be added
        # after the basic connection flow is tested.
        ZohoOAuthRepository.delete_connection(
            user_id
        )