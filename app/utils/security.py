"""Password hashing and JWT token handling."""
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from passlib.context import CryptContext

from app.config import settings


_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return _pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_access_token(
    subject: str | int,
    extra_claims: Optional[dict] = None,
    expires_minutes: Optional[int] = None,
) -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    expires_minutes = expires_minutes or settings.access_token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload: dict = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": settings.app_name,
    }
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token, expires_minutes * 60


def decode_token(token: str) -> dict:
    """Decode a JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
        options={"require": ["exp", "sub"]},
    )
