import secrets
from fastapi import Request, HTTPException

from app.config import get_settings

_active_tokens: set[str] = set()


def create_token() -> str:
    token = secrets.token_hex(32)
    _active_tokens.add(token)
    return token


def verify_token(token: str) -> bool:
    return token in _active_tokens


async def require_admin(request: Request) -> None:
    settings = get_settings()
    if not settings.admin_password:
        return  # No password set = auth disabled

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    token = auth_header[7:]
    if not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
