"""JWT authentication utilities."""

import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings

security = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


def create_token(password: str) -> str:
    """Create a JWT token if the password matches."""
    if password != settings.app_password:
        raise HTTPException(status_code=401, detail="密码错误")

    payload = {
        "sub": "user",
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    """Verify a JWT token, return payload or raise."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的登录凭证")


async def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    """Dependency: require valid JWT token for API access."""
    path = request.url.path

    # Skip auth for non-API routes (static files, SPA pages)
    if not path.startswith("/api/"):
        return

    # Allow health check and login without auth
    if path in ("/api/v1/health", "/api/v1/auth/login"):
        return

    if credentials is None:
        raise HTTPException(status_code=401, detail="请先登录")

    token = credentials.credentials
    verify_token(token)
    return
