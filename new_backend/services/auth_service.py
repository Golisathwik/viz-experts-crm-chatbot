"""
Authentication Service
----------------------
Contains all business logic related to authentication.
"""

from new_backend.auth.password_handler import (
    hash_password,
    verify_password,
)

from new_backend.auth.jwt_handler import (
    create_access_token,
)

from new_backend.repositories.user_repository import (
    UserRepository,
)


class AuthService:

    @staticmethod
    def signup(full_name: str, email: str, password: str):

        email = email.strip().lower()

        existing_user = UserRepository.get_user_by_email(
            email
        )

        if existing_user:

            return {
                "success": False,
                "field": "email",
                "message": "This email address already exists."
            }

        password_hash = hash_password(
            password
        )

        user_id = UserRepository.create_user(
            full_name=full_name,
            email=email,
            password_hash=password_hash
        )

        if not user_id:

            return {
                "success": False,
                "field": "email",
                "message": "This email address already exists."
            }

        token = create_access_token({
            "user_id": user_id,
            "email": email
        })

        return {
            "success": True,
            "message": "Your account has been created successfully.",
            "token": token,
            "full_name": full_name
        }

    @staticmethod
    def login(email: str, password: str):

        user = UserRepository.get_user_by_email(email)

        if not user:
            return {
                "success": False,
                "field": "email",
                "message": "Invalid email or password."
            }

        if not verify_password(
            password,
            user["password_hash"]
        ):
            return {
                "success": False,
                "field": "password",
                "message": "Invalid email or password."
            }

        token = create_access_token({
            "user_id": user["id"],
            "email": user["email"]
        })

        return {
            "success": True,
            "message": "Login successful.",
            "token": token,
            "full_name": user["full_name"]
        }