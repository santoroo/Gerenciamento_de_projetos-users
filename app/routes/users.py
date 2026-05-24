"""User management endpoints (admin-managed CRUD).

Self-registration lives in /api/auth/register. These routes are mostly for admins."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Role, User
from app.schemas import (
    UserCreate,
    UserDetailResponse,
    UserResponse,
    UserUpdate,
)
from app.utils.dependencies import get_current_user, require_admin
from app.utils.security import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a user with an explicit role. Admin only."""
    dup = (await db.execute(
        select(User).where((User.email == payload.email) | (User.username == payload.username))
    )).scalar_one_or_none()
    if dup:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username or email already registered")

    role = (await db.execute(select(Role).where(Role.id == payload.role_id))).scalar_one_or_none()
    if not role:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Role not found")

    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role_id=payload.role_id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/", response_model=list[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List users (any authenticated user can browse the directory)."""
    result = await db.execute(select(User).offset(skip).limit(limit).order_by(User.id))
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Users can edit themselves; admins can edit anyone.
    Only admins may change ``role_id`` or ``is_active``."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    is_self = current_user.id == user_id
    is_admin = current_user.role and current_user.role.name == "admin"
    if not (is_self or is_admin):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot edit another user")

    data = payload.model_dump(exclude_unset=True)
    privileged = {"role_id", "is_active"}
    if not is_admin:
        for field in privileged.intersection(data):
            data.pop(field)

    if "role_id" in data:
        role = (await db.execute(select(Role).where(Role.id == data["role_id"]))).scalar_one_or_none()
        if not role:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Role not found")

    if "email" in data and data["email"] != user.email:
        dup = (await db.execute(select(User).where(User.email == data["email"]))).scalar_one_or_none()
        if dup:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already in use")

    for field, value in data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Soft-delete (deactivate) a user. Admin only."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.is_active = False
    await db.commit()


@router.get("/roles/list", response_model=list[dict])
async def list_roles(db: AsyncSession = Depends(get_db)):
    """List available roles (public — used by registration forms)."""
    result = await db.execute(select(Role).order_by(Role.id))
    return [
        {"id": r.id, "name": r.name, "description": r.description}
        for r in result.scalars().all()
    ]
