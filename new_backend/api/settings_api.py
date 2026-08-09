from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from new_backend.auth.dependencies import get_current_user_id
from new_backend.repositories.user_repository import UserRepository
from new_backend.auth.password_handler import verify_password, hash_password

router = APIRouter(
    prefix="/settings",
    tags=["Settings"]
)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    user_id: int = Depends(get_current_user_id)
):

    user = UserRepository.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    if not verify_password(
        data.old_password,
        user["password_hash"]
    ):
        raise HTTPException(
            status_code=400,
            detail="Old password is incorrect."
        )

    UserRepository.update_user_password(
        user_id,
        hash_password(data.new_password)
    )

    return {
        "success": True,
        "message": "Password updated successfully."
    }