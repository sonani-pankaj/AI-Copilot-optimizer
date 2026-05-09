# See: specs/OVERVIEW.md — JWT Authentication
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

_SECRET_KEY: Optional[str] = os.environ.get("JWT_SECRET")
if not _SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET environment variable is required. "
        "Set it in your .env file or docker-compose.yml."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

_security = HTTPBearer()


class TokenData(BaseModel):
    user_id: str
    team_id: Optional[str] = None


def create_access_token(user_id: str, team_id: Optional[str] = None) -> str:
    """Encode a JWT for the given user."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "team_id": team_id, "exp": expire}
    return jwt.encode(payload, _SECRET_KEY, algorithm=ALGORITHM)


def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
) -> TokenData:
    """FastAPI dependency: validates JWT and returns TokenData."""
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, _SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            raise exc
        return TokenData(user_id=user_id, team_id=payload.get("team_id"))
    except JWTError:
        raise exc
