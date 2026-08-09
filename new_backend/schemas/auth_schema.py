from typing import Optional
from pydantic import BaseModel, EmailStr


class UserSignupRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class ConfigSaveRequest(BaseModel):
    zoho_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None


class TestConfigRequest(BaseModel):
    zoho_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str