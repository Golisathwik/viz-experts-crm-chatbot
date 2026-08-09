"""
Authentication API
------------------
Authentication endpoints.
"""

from fastapi import APIRouter

from new_backend.controllers.auth_controller import AuthController

from new_backend.models.request_models import (
    UserSignupRequest,
    UserLoginRequest,
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/signup")
async def signup(request: UserSignupRequest):

    return await AuthController.signup(request)


@router.post("/login")
async def login(request: UserLoginRequest):

    return await AuthController.login(request)

from pydantic import BaseModel

class ForgotPasswordRequest(BaseModel):
    email: str

@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest):
    return {
        "success": True,
        "message": "Password reset feature coming soon."
    }