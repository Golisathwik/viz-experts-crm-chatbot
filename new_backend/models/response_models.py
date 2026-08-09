"""
Response Models
---------------
Standard API response models.
"""

from typing import Any
from typing import Optional

from pydantic import BaseModel


class ApiResponse(BaseModel):

    success: bool

    message: str

    data: Optional[Any] = None


class LoginResponse(BaseModel):

    success: bool

    message: str

    token: str

    full_name: str


class ErrorResponse(BaseModel):

    success: bool = False

    message: str