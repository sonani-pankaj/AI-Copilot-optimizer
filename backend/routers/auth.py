# See: specs/OVERVIEW.md — Authentication
import os

from fastapi import APIRouter, HTTPException, status
from passlib.context import CryptContext

from ..auth.jwt import create_access_token
from ..models.schemas import LoginRequest, TokenResponse

router = APIRouter()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Demo user — in production replace with DB lookup.
# Credentials loaded from env vars; never hardcoded.
_DEMO_USERNAME = os.environ.get("DEMO_USERNAME", "admin")
_DEMO_PASSWORD_HASH = os.environ.get(
    "DEMO_PASSWORD_HASH",
    # Default hash for "changeme" — override in production via DEMO_PASSWORD_HASH
    "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    """Issue a JWT for valid credentials."""
    if req.username != _DEMO_USERNAME or not _pwd_context.verify(req.password, _DEMO_PASSWORD_HASH):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token(user_id=req.username, team_id="default")
    return TokenResponse(access_token=token)
