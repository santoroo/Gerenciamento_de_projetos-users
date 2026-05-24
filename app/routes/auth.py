"""Authentication and session validation endpoints.

This module exposes:
  POST /api/auth/register      — public self-registration (always 'contributor')
  POST /api/auth/login         — JSON login, returns JWT
  POST /api/auth/login-form    — OAuth2 password-form login (used by Swagger UI)
  GET  /api/auth/me            — current user (requires Bearer token)
  GET  /api/auth/validate      — token validation for *other microservices*
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Role, RoleEnum, User
from app.schemas import (
    LoginRequest,
    TokenResponse,
    TokenValidationResponse,
    UserDetailResponse,
    UserRegister,
)
from app.utils.dependencies import get_current_user, oauth2_scheme
from app.utils.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
import jwt as _jwt

router = APIRouter(prefix="/api/auth", tags=["auth"])


async def _resolve_default_contributor_role(db: AsyncSession) -> Role:
    result = await db.execute(select(Role).where(Role.name == RoleEnum.CONTRIBUTOR.value))
    role = result.scalar_one_or_none()
    if role is None:
        # Bootstrap: create the basic roles if the DB is empty.
        for name, desc in (
            (RoleEnum.ADMIN.value, "Tech Lead / Arquiteto — full access"),
            (RoleEnum.MANAGER.value, "Gerente de Projetos — manages teams/projects"),
            (RoleEnum.CONTRIBUTOR.value, "Desenvolvedor — limited access"),
        ):
            existing = (await db.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
            if not existing:
                db.add(Role(name=name, description=desc))
        await db.commit()
        result = await db.execute(select(Role).where(Role.name == RoleEnum.CONTRIBUTOR.value))
        role = result.scalar_one()
    return role


async def _build_token_response(user: User, db: AsyncSession) -> TokenResponse:
    role_name = user.role.name if user.role else None
    token, expires_in = create_access_token(
        subject=user.id,
        extra_claims={"username": user.username, "role": role_name},
    )
    # Re-fetch to ensure relationships are loaded for the response model.
    refreshed = (await db.execute(select(User).where(User.id == user.id))).scalar_one()
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserDetailResponse.model_validate(refreshed),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    """Public registration. New users always get the 'contributor' role."""
    existing = (await db.execute(
        select(User).where(or_(User.email == payload.email, User.username == payload.username))
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered",
        )

    role = await _resolve_default_contributor_role(db)
    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return await _build_token_response(user, db)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """JSON login. Accepts username or email in ``username_or_email``."""
    result = await db.execute(
        select(User).where(
            or_(User.email == payload.username_or_email, User.username == payload.username_or_email)
        )
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
    return await _build_token_response(user, db)


@router.post("/login-form", response_model=TokenResponse, include_in_schema=False)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """OAuth2-password-form variant so Swagger's 'Authorize' works."""
    return await login(
        LoginRequest(username_or_email=form_data.username, password=form_data.password),
        db=db,
    )


@router.get("/me", response_model=UserDetailResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user (used by frontend and other modules)."""
    return current_user


@router.get("/validate", response_model=TokenValidationResponse)
async def validate_token(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Token validation endpoint for sibling microservices.

    Returns 200 always (with ``valid=False`` on failure) so callers can branch
    cleanly instead of catching exceptions across the network.
    """
    if not token:
        return TokenValidationResponse(valid=False)
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except (_jwt.PyJWTError, ValueError, KeyError):
        return TokenValidationResponse(valid=False)

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user or not user.is_active:
        return TokenValidationResponse(valid=False, user_id=user_id, is_active=False)

    return TokenValidationResponse(
        valid=True,
        user_id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.name if user.role else None,
        is_active=user.is_active,
    )
