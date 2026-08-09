"""
Authentication Controller
-------------------------
Acts as a bridge between API and Service.
"""

from new_backend.models.request_models import (
    UserSignupRequest,
    UserLoginRequest,
)

from new_backend.services.auth_service import AuthService

class AuthController:

    @staticmethod
    async def signup(request: UserSignupRequest):

        return AuthService.signup(
            full_name=request.full_name,
            email=request.email,
            password=request.password
        )

    @staticmethod
    async def login(request: UserLoginRequest):

        return AuthService.login(
            email=request.email,
            password=request.password
        )