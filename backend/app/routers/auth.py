"""Authentication API routes."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.auth import create_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str = Field(..., description="登录密码")


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest):
    """Login with password, receive JWT token."""
    token = create_token(data.password)
    return LoginResponse(token=token)


@router.get("/check")
async def check_auth():
    """Verify token is valid. Protected by require_auth middleware."""
    return {"status": "ok"}
