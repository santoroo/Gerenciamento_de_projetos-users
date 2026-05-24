"""Project management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import PROJECT_MEMBER_ROLES, Project, ProjectMember, Team, User
from app.schemas import (
    MessageResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.rbac import RBACService
from app.utils.dependencies import get_current_user, require_manager_or_admin

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _project_to_response(project: Project) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "tags": project.tags,
        "team_id": project.team_id,
        "owner_id": project.owner_id,
        "is_active": project.is_active,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "members": [
            {
                "user_id": m.user_id,
                "username": m.user.username if m.user else "",
                "email": m.user.email if m.user else "",
                "role": m.role,
                "joined_at": m.joined_at,
            }
            for m in (project.members or [])
        ],
    }


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    """Create a project. Manager/admin only. Caller is the owner and becomes a project admin."""
    if payload.team_id is not None:
        team = (await db.execute(
            select(Team).where(Team.id == payload.team_id)
        )).scalar_one_or_none()
        if not team:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")
        if not await RBACService.has_team_access(current_user.id, payload.team_id, db):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't have access to this team")

    project = Project(
        name=payload.name,
        description=payload.description,
        tags=payload.tags,
        team_id=payload.team_id,
        owner_id=current_user.id,
        is_active=True,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    db.add(ProjectMember(project_id=project.id, user_id=current_user.id, role="admin"))
    await db.commit()

    full = (await db.execute(
        select(Project).options(selectinload(Project.members).selectinload(ProjectMember.user))
        .where(Project.id == project.id)
    )).scalar_one()
    return _project_to_response(full)


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    include_inactive: bool = False,
    mine: bool = Query(False, description="Return only projects the current user belongs to"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Project).options(
        selectinload(Project.members).selectinload(ProjectMember.user)
    )
    if not include_inactive:
        stmt = stmt.where(Project.is_active == True)  # noqa: E712
    if mine:
        stmt = stmt.join(ProjectMember, ProjectMember.project_id == Project.id) \
                   .where(ProjectMember.user_id == current_user.id)
    stmt = stmt.offset(skip).limit(limit).order_by(Project.id)
    result = await db.execute(stmt)
    return [_project_to_response(p) for p in result.scalars().unique().all()]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    project = (await db.execute(
        select(Project).options(selectinload(Project.members).selectinload(ProjectMember.user))
        .where(Project.id == project_id)
    )).scalar_one_or_none()
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return _project_to_response(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    if not await RBACService.is_project_admin(current_user.id, project_id, db) \
            and project.owner_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only project admins can update this project")

    data = payload.model_dump(exclude_unset=True)
    if "team_id" in data and data["team_id"] is not None:
        team = (await db.execute(select(Team).where(Team.id == data["team_id"]))).scalar_one_or_none()
        if not team:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")

    for field, value in data.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)
    full = (await db.execute(
        select(Project).options(selectinload(Project.members).selectinload(ProjectMember.user))
        .where(Project.id == project.id)
    )).scalar_one()
    return _project_to_response(full)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if not await RBACService.is_project_admin(current_user.id, project_id, db) \
            and project.owner_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only project admins can archive this project")
    project.is_active = False
    await db.commit()


@router.post("/{project_id}/members/{user_id}", response_model=MessageResponse,
             status_code=status.HTTP_201_CREATED)
async def add_project_member(
    project_id: int,
    user_id: int,
    role: str = Query("contributor"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if role not in PROJECT_MEMBER_ROLES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid role. Must be one of: {', '.join(PROJECT_MEMBER_ROLES)}",
        )

    project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    if not await RBACService.is_project_admin(current_user.id, project_id, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only project admins can add members")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    existing = (await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already a project member")

    db.add(ProjectMember(project_id=project_id, user_id=user_id, role=role))
    await db.commit()
    return MessageResponse(message=f"User added to project with role: {role}")


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    project_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    if not await RBACService.is_project_admin(current_user.id, project_id, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only project admins can remove members")

    member = (await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )).scalar_one_or_none()
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found in project")

    await db.delete(member)
    await db.commit()
