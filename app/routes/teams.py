from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Team, TeamMember, User
from app.schemas import TeamCreate, TeamResponse, TeamUpdate
from app.services.rbac import RBACService

router = APIRouter(prefix="/api/teams", tags=["teams"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamCreate,
    owner_id: int,  # In production, get from JWT token
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new team

    Only authenticated users can create teams.
    User becomes the team owner.
    """
    # Verify owner exists
    query = select(User).where(User.id == owner_id)
    result = await db.execute(query)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    new_team = Team(
        name=team_data.name,
        description=team_data.description,
        owner_id=owner_id
    )

    db.add(new_team)
    await db.commit()
    await db.refresh(new_team)

    return new_team


@router.get("/", response_model=list[TeamResponse])
async def list_teams(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all active teams"""
    query = select(Team).where(Team.is_active ==
                               True).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get team details with members"""
    query = select(Team).where(Team.id == team_id)
    result = await db.execute(query)
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    return team


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    team_data: TeamUpdate,
    current_user_id: int,  # In production, from JWT
    db: AsyncSession = Depends(get_db)
):
    """
    Update team information

    RBAC: Only team owner or admin can update
    """
    query = select(Team).where(Team.id == team_id)
    result = await db.execute(query)
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    # Check authorization
    is_owner = team.owner_id == current_user_id
    is_admin = await RBACService.check_user_role(
        current_user_id,
        ["admin"],
        db
    )

    if not (is_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only team owner or admin can update this team"
        )

    # Update fields
    update_data = team_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(team, field, value)

    await db.commit()
    await db.refresh(team)

    return team


@router.post("/{team_id}/members/{user_id}", status_code=status.HTTP_201_CREATED)
async def add_team_member(
    team_id: int,
    user_id: int,
    current_user_id: int,  # In production, from JWT
    db: AsyncSession = Depends(get_db)
):
    """
    Add user to team

    RBAC: Only team owner or admin
    """
    query = select(Team).where(Team.id == team_id)
    result = await db.execute(query)
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    # Verify authorization
    is_owner = team.owner_id == current_user_id
    is_admin = await RBACService.check_user_role(
        current_user_id,
        ["admin"],
        db
    )

    if not (is_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only team owner or admin can add members"
        )

    # Verify user exists
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if already member
    query = select(TeamMember).where(
        (TeamMember.team_id == team_id) & (TeamMember.user_id == user_id)
    )
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a team member"
        )

    member = TeamMember(team_id=team_id, user_id=user_id)
    db.add(member)
    await db.commit()

    return {"message": "User added to team"}


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    team_id: int,
    user_id: int,
    current_user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Remove user from team"""
    query = select(Team).where(Team.id == team_id)
    result = await db.execute(query)
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    # Verify authorization
    is_owner = team.owner_id == current_user_id
    is_admin = await RBACService.check_user_role(
        current_user_id,
        ["admin"],
        db
    )

    if not (is_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only team owner or admin can remove members"
        )

    query = select(TeamMember).where(
        (TeamMember.team_id == team_id) & (TeamMember.user_id == user_id)
    )
    result = await db.execute(query)
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in team"
        )

    await db.delete(member)
    await db.commit()
