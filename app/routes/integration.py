"""Endpoints designed to be consumed by *other* microservices in the platform.

These complement /api/auth/validate (which authenticates a user token) and
expose stable, narrow shapes so sibling teams don't depend on internals."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Project, ProjectMember, User
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/api/integration", tags=["integration"])


# ---- minimal shapes (kept separate from app schemas so changes here are intentional) ----
class UserMini(BaseModel):
    id: int
    username: str
    email: str
    full_name: str | None = None
    role: str
    is_active: bool


class ProjectAccess(BaseModel):
    project_id: int
    user_id: int
    has_access: bool
    role: str | None = None  # the user's role within the project (if member)


# ---------------- endpoints ----------------
@router.get("/users/lookup", response_model=List[UserMini])
async def lookup_users(
    ids: str = Query(..., description="Comma-separated user ids (max 100)", example="1,2,3"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Bulk fetch user records by id.

    Used by sibling modules (Reports, Diagrams, Chat...) to enrich UI listings
    with usernames/emails without paginating through /api/users."""
    try:
        id_list = [int(x) for x in ids.split(",") if x.strip()][:100]
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid id list — must be integers")

    if not id_list:
        return []

    result = await db.execute(select(User).where(User.id.in_(id_list)))
    return [
        UserMini(
            id=u.id,
            username=u.username,
            email=u.email,
            full_name=u.full_name,
            role=u.role.name if u.role else "",
            is_active=u.is_active,
        )
        for u in result.scalars().all()
    ]


@router.get("/projects/{project_id}/access/{user_id}", response_model=ProjectAccess)
async def check_project_access(
    project_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Tell a sibling module whether a given user can act on a given project.

    Used e.g. by the Reports module before allowing report generation, or by
    the Chat module before exposing a project's documents."""
    project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    if project.owner_id == user_id:
        return ProjectAccess(project_id=project_id, user_id=user_id, has_access=True, role="owner")

    member = (await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )).scalar_one_or_none()

    if member:
        return ProjectAccess(project_id=project_id, user_id=user_id, has_access=True, role=member.role)
    return ProjectAccess(project_id=project_id, user_id=user_id, has_access=False, role=None)
