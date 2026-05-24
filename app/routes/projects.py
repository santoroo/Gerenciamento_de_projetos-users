from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database import AsyncSessionLocal
from app.models import Project, ProjectMember, Team, User, TeamMember
from app.schemas import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.rbac import RBACService

router = APIRouter(prefix="/api/projects", tags=["projects"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    owner_id: int,  # In production, from JWT
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new project with team assignment

    Complex RBAC Logic:
    - Only Managers and Admins can create projects
    - If team_id provided:
        - User must be team owner or admin
        - User will be added as project member
    - Project owner will be added as project member

    Tags are used for AI recommendations (comma-separated)
    """
    # 1. Verify user is manager or admin
    await RBACService.ensure_manager_or_admin(owner_id, db)

    # 2. Verify owner exists
    query = select(User).where(User.id == owner_id)
    result = await db.execute(query)
    owner = result.scalar_one_or_none()
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner user not found"
        )

    # 3. If team specified, verify access and permissions
    team = None
    if project_data.team_id:
        query = select(Team).where(Team.id == project_data.team_id)
        result = await db.execute(query)
        team = result.scalar_one_or_none()

        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )

        # Verify user has access to assign team
        has_team_access = await RBACService.verify_team_access(
            owner_id,
            project_data.team_id,
            db
        )
        if not has_team_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this team"
            )

    # 4. Create project
    new_project = Project(
        name=project_data.name,
        description=project_data.description,
        tags=project_data.tags,
        team_id=project_data.team_id,
        owner_id=owner_id
    )

    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    # 5. Add owner as project member
    owner_member = ProjectMember(
        project_id=new_project.id,
        user_id=owner_id,
        role="admin"  # Owner has admin role on project
    )
    db.add(owner_member)
    await db.commit()

    return new_project


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all active projects"""
    query = select(Project).where(
        Project.is_active == True
    ).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get project details with members"""
    query = select(Project).where(Project.id == project_id)
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    current_user_id: int,  # In production, from JWT
    db: AsyncSession = Depends(get_db)
):
    """
    Update project information

    RBAC: Only project owner or admin can update
    """
    query = select(Project).where(Project.id == project_id)
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Check authorization - must be project owner or admin in app
    is_owner = project.owner_id == current_user_id
    is_admin = await RBACService.check_user_role(
        current_user_id,
        ["admin"],
        db
    )

    if not (is_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project owner or admin can update this project"
        )

    # Update fields
    update_data = project_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)

    return project


@router.post("/{project_id}/members/{user_id}", status_code=status.HTTP_201_CREATED)
async def add_project_member(
    project_id: int,
    user_id: int,
    role: str = "contributor",  # admin, editor, viewer, contributor
    current_user_id: int = None,  # In production, from JWT
    db: AsyncSession = Depends(get_db)
):
    """
    Add user to project with specific role

    RBAC Logic:
    - Only project admin (owner) can add members
    - Can assign roles: admin, editor, viewer, contributor
    """
    query = select(Project).where(Project.id == project_id)
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Verify authorization - user must be project admin
    query = select(ProjectMember).where(
        and_(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user_id
        )
    )
    result = await db.execute(query)
    member = result.scalar_one_or_none()

    if not member or member.role != "admin":
        # Check if user is app admin
        is_app_admin = await RBACService.check_user_role(
            current_user_id,
            ["admin"],
            db
        )
        if not is_app_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only project admin or app admin can add members"
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
    query = select(ProjectMember).where(
        and_(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        )
    )
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a project member"
        )

    # Validate role
    valid_roles = ["admin", "editor", "viewer", "contributor"]
    if role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )

    # Add member
    new_member = ProjectMember(
        project_id=project_id,
        user_id=user_id,
        role=role
    )
    db.add(new_member)
    await db.commit()

    return {"message": f"User added to project with role: {role}"}


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    project_id: int,
    user_id: int,
    current_user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Remove user from project"""
    query = select(Project).where(Project.id == project_id)
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Verify authorization
    query = select(ProjectMember).where(
        and_(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user_id
        )
    )
    result = await db.execute(query)
    requester = result.scalar_one_or_none()

    if not requester or requester.role != "admin":
        is_app_admin = await RBACService.check_user_role(
            current_user_id,
            ["admin"],
            db
        )
        if not is_app_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only project admin can remove members"
            )

    query = select(ProjectMember).where(
        and_(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        )
    )
    result = await db.execute(query)
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in project"
        )

    await db.delete(member)
    await db.commit()
