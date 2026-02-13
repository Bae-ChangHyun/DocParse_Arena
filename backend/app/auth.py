from datetime import datetime, timezone

import jwt
from fastapi import Request, HTTPException

from app.config import get_settings


def create_token() -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "admin",
        "iat": now,
        "exp": datetime.fromtimestamp(
            now.timestamp() + settings.jwt_expiry_minutes * 60,
            tz=timezone.utc,
        ),
    }
    return jwt.encode(payload, settings.get_jwt_secret(), algorithm="HS256")


def verify_token(token: str) -> bool:
    settings = get_settings()
    try:
        jwt.decode(token, settings.get_jwt_secret(), algorithms=["HS256"])
        return True
    except jwt.PyJWTError:
        return False


async def require_admin(request: Request) -> None:
    settings = get_settings()
    if not settings.admin_password:
        raise HTTPException(
            status_code=403,
            detail="Admin access disabled. Set ADMIN_PASSWORD in .env",
        )

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    token = auth_header[7:]
    if not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
