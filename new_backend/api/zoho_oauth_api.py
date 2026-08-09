from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from new_backend.auth.dependencies import get_current_user_id
from new_backend.services.zoho_oauth_service import (
    ZohoOAuthService,
)


router = APIRouter(
    prefix="/auth/zoho",
    tags=["Zoho OAuth"],
)


class ZohoConnectRequest(BaseModel):

    client_id: str = Field(
        ...,
        min_length=1,
        max_length=500,
    )

    client_secret: str = Field(
        ...,
        min_length=1,
        max_length=1000,
    )


@router.post("/connect")
def connect_zoho(
    request: ZohoConnectRequest,
    user_id: int = Depends(get_current_user_id),
):

    try:

        authorization_url = (
            ZohoOAuthService.create_authorization_url(
                user_id=user_id,
                client_id=request.client_id,
                client_secret=request.client_secret,
            )
        )

        return {
            "success": True,
            "authorization_url": authorization_url,
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Unable to start Zoho authorization.",
        )


@router.get("/status")
def zoho_status(
    user_id: int = Depends(get_current_user_id),
):

    return ZohoOAuthService.get_connection_status(
        user_id
    )


@router.post("/disconnect")
def disconnect_zoho(
    user_id: int = Depends(get_current_user_id),
):

    ZohoOAuthService.disconnect(
        user_id
    )

    return {
        "success": True,
        "connected": False,
    }


@router.get("/callback")
async def zoho_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):

    if error:

        return RedirectResponse(
            url=(
                "/?zoho_error="
                + error
            )
        )

    if not code or not state:

        return RedirectResponse(
            url=(
                "/?zoho_error="
                "missing_authorization_response"
            )
        )

    try:

        await ZohoOAuthService.exchange_code(
            state=state,
            code=code,
        )

        return RedirectResponse(
            url="/?zoho_connected=true"
        )

    except ValueError as exc:

        return RedirectResponse(
            url=(
                "/?zoho_error="
                + str(exc)
            )
        )

    except Exception:

        return RedirectResponse(
            url=(
                "/?zoho_error="
                "authorization_failed"
            )
        )