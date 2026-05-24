"""Team management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Team, TeamMember, User
from app.schemas import MessageResponse, TeamCreate, TeamResponse, TeamUpdate
from app.services.rbac import RBACService
from app.utils.dependencies import get_current_user, require_manager_or_admin

router = APIRouter(prefix="/api/teams", tags=["teams"])


def _team_to_response(team: Team) -> dict:
    return {
        "id": team.id,
        "name": team.name,
        "description": team.description,
        "owner_id": team.owner_id,
        "is_active": team.is_active,
        "created_at": team.created_at,
        "updated_at": team.updated_at,
        "members": [
            {
                "user_id": m.user_id,
                "username": m.user.username if m.user else "",
                "email": m.user.email if m.user else "",
                "full_name": m.user.full_name if m.user else None,
                "joined_at": m.joined_at,
            }
            for m in (team.members or [])
        ],
    }


@router.post("/", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    payload: TeamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    """Create a team. Caller becomes the owner. Managers/admins only."""
    team = Team(
        name=payload.name,
        description=payload.description,
        owner_id=current_user.id,
        is_active=True,
    )
    db.add(team)
    await db.commit()
    await db.refresh(team)

    full = (await db.execute(
        select(Team).options(selectinload(Team.members).selectinload(TeamMember.user))
        .where(Team.id == team.id)
    )).scalar_one()
    return _team_to_response(full)


@router.get("/", response_model=list[TeamResponse])
async def list_teams(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Team).options(selectinload(Team.members).selectinload(TeamMember.user))
    if not include_inactive:
        stmt = stmt.where(Team.is_active == True)  # noqa: E712
    stmt = stmt.offset(skip).limit(limit).order_by(Team.id)
    result = await db.execute(stmt)
    return [_team_to_response(t) for t in result.scalars().all()]


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    team = (await db.execute(
        select(Team).options(selectinload(Team.members).selectinload(TeamMember.user))
        .where(Team.id == team_id)
    )).scalar_one_or_none()
    if not team:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")
    return _team_to_response(team)


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    payload: TeamUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = (await db.execute(select(Team).where(Team.id == team_id))).scalar_one_or_none()
    if not team:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")

    is_owner = team.owner_id == current_user.id
    is_admin = await RBACService.is_admin(current_user.id, db)
    if not (is_owner or is_admin):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the team owner or an admin can update this team")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(team, field, value)

    await db.commit()
    await db.refresh(team)
    full = (await db.execute(
        select(Team).options(selectinload(Team.members).selectinload(TeamMember.user))
        .where(Team.id == team.id)
    )).scalar_one()
    return _team_to_response(full)


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete (archive) a team."""
    team = (await db.execute(select(Team).where(Team.id == team_id))).scalar_one_or_none()
    if not team:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")
    if team.owner_id != current_user.id and not await RBACService.is_admin(current_user.id, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the team owner or an admin can archive this team")
    team.is_active = False
    await db.commit()


@router.post("/{team_id}/members/{user_id}", response_model=MessageResponse,
             status_code=status.HTTP_201_CREATED)
async def add_team_member(
    team_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = (await db.execute(select(Team).where(Team.id == team_id))).scalar_one_or_none()
    if not team:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")

    if team.owner_id != current_user.id and not await RBACService.is_admin(current_user.id, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the team owner or an admin can add members")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    existing = (await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already a team member")

    db.add(TeamMember(team_id=team_id, user_id=user_id))
    await db.commit()
    return MessageResponse(message="User added to team")


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    team_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = (await db.execute(select(Team).where(Team.id == team_id))).scalar_one_or_none()
    if not team:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")

    if team.owner_id != current_user.id and not await RBACService.is_admin(current_user.id, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the team owner or an admin can remove members")

    member = (await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )).scalar_one_or_none()
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found in team")

    await db.delete(member)
    await db.commit()
