from fastapi import APIRouter, Depends, HTTPException
import httpx

from new_backend.schemas.auth_schema import (
    ConfigSaveRequest,
    TestConfigRequest
)
from new_backend.auth.dependencies import get_current_user_id
from new_backend.repositories.config_repository import ConfigRepository
from new_backend.crm.zoho_client import ZohoCRMClient

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

DEFAULT_MODEL = "llama-3.3-70b-versatile"

router = APIRouter(prefix="/config", tags=["Configuration"])


@router.get("")
def get_configuration(
    user_id: int = Depends(get_current_user_id)
):
    config = ConfigRepository.get_config(user_id)

    if not config:
        return {
            "configured": False,
            "zoho_configured": False,
            "groq_configured": False,
            "gemini_configured": False
        }

    # Zoho CRM is connected through OAuth.
    # It is NOT represented by a Zoho API key in this configuration endpoint.
    groq_key = config.get("groq_api_key") or ""
    gemini_key = config.get("gemini_api_key") or ""

    return {
        # This flag represents whether at least one LLM key is configured.
        # The frontend combines it with /auth/zoho/status for full readiness.
        "configured": bool(groq_key or gemini_key),

        # Kept for compatibility. The real Zoho state comes from OAuth status.
        "zoho_configured": False,

        "groq_configured": bool(groq_key),
        "gemini_configured": bool(gemini_key),

        "groq_masked": (
            f"{groq_key[:6]}...{groq_key[-4:]}"
            if len(groq_key) > 10 else ""
        ),

        "gemini_masked": (
            f"{gemini_key[:6]}...{gemini_key[-4:]}"
            if len(gemini_key) > 10 else ""
        )
    }


@router.post("/save")
def save_configuration(
    request: ConfigSaveRequest,
    user_id: int = Depends(get_current_user_id)
):
    ConfigRepository.save_config(
        user_id=user_id,
        zoho_api_key=request.zoho_api_key,
        groq_api_key=request.groq_api_key,
        gemini_api_key=request.gemini_api_key
    )

    return {
        "message": "Configuration saved successfully"
    }


@router.post("/test-zoho")
def test_zoho(
    user_id: int = Depends(get_current_user_id)
):
    try:
        client = ZohoCRMClient(
            user_id=user_id
        )

        if client.test_connection():
            return {
                "success": True,
                "message": "Zoho CRM connection successful"
            }

        raise HTTPException(
            status_code=400,
            detail="Unable to connect to Zoho CRM"
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )


@router.post("/test-groq")
async def test_groq(
    request: TestConfigRequest,
    user_id: int = Depends(get_current_user_id)
):
    api_key = (request.groq_api_key or "").strip()

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="Please enter a Groq API key."
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": DEFAULT_MODEL,
                    "messages": [
                        {
                            "role": "user",
                            "content": "Reply with OK."
                        }
                    ],
                    "max_tokens": 5
                },
                timeout=10
            )

        if response.status_code == 200:
            return {
                "success": True,
                "message": "Groq API key is valid and connected."
            }

        try:
            error_data = response.json()
            error_message = (
                error_data.get("error", {}).get("message")
                or "Groq API key validation failed."
            )
        except Exception:
            error_message = "Groq API key validation failed."

        raise HTTPException(
            status_code=400,
            detail=error_message
        )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=400,
            detail="Groq connection timed out. Please try again."
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=400,
            detail="Unable to reach Groq API. Please check your internet connection."
        )
    
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-3.6-flash:generateContent"
)


@router.post("/test-gemini")
async def test_gemini(
    request: TestConfigRequest,
    user_id: int = Depends(get_current_user_id)
):
    api_key = (request.gemini_api_key or "").strip()

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="Please enter a Gemini API key."
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GEMINI_API_URL,
                headers={
                    "x-goog-api-key": api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": "Reply with OK."
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "maxOutputTokens": 5
                    }
                },
                timeout=10
            )

        if response.status_code == 200:
            return {
                "success": True,
                "message": "Gemini API key is valid and connected."
            }

        try:
            error_data = response.json()

            error_message = (
                error_data.get("error", {}).get("message")
                or "Gemini API key validation failed."
            )

        except Exception:
            error_message = "Gemini API key validation failed."

        raise HTTPException(
            status_code=400,
            detail=error_message
        )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=400,
            detail="Gemini connection timed out. Please try again."
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=400,
            detail="Unable to reach Gemini API. Please check your internet connection."
        )