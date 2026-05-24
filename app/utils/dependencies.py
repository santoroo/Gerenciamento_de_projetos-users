"""Common FastAPI dependencies: DB session, current user, role guards."""
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, RoleEnum
from app.utils.security import decode_token


# tokenUrl points to our login endpoint so Swagger's "Authorize" button works.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login-form", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a Bearer JWT.
    Raises 401 if missing/invalid/expired or the user is inactive."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    try:
        payload = decode_token(token)
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
    return user


def require_roles(*allowed: RoleEnum | str):
    """Build a dependency that enforces the current user has one of the given roles."""
    allowed_names = {r.value if isinstance(r, RoleEnum) else r for r in allowed}

    async def _guard(current_user: User = Depends(get_current_user)) -> User:
        role_name = current_user.role.name if current_user.role else None
        if role_name not in allowed_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role(s): {', '.join(sorted(allowed_names))}",
            )
        return current_user

    return _guard


# Convenience guards
require_admin = require_roles(RoleEnum.ADMIN)
require_manager_or_admin = require_roles(RoleEnum.ADMIN, RoleEnum.MANAGER)
