from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User, Role, RoleEnum
from fastapi import HTTPException, status


class RBACService:
    """Role-Based Access Control Service"""

    @staticmethod
    async def check_user_role(
        user_id: int,
        required_roles: list[RoleEnum],
        db: AsyncSession
    ) -> bool:
        """Check if user has one of the required roles"""
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            return False

        query = select(Role).where(Role.id == user.role_id)
        result = await db.execute(query)
        role = result.scalar_one_or_none()

        if not role:
            return False

        return role.name in required_roles

    @staticmethod
    async def ensure_admin(user_id: int, db: AsyncSession):
        """Ensure user is admin, raise exception otherwise"""
        is_admin = await RBACService.check_user_role(
            user_id,
            [RoleEnum.ADMIN],
            db
        )
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can perform this action"
            )

    @staticmethod
    async def ensure_manager_or_admin(user_id: int, db: AsyncSession):
        """Ensure user is manager or admin"""
        has_permission = await RBACService.check_user_role(
            user_id,
            [RoleEnum.ADMIN, RoleEnum.MANAGER],
            db
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only managers and admins can perform this action"
            )

    @staticmethod
    async def verify_project_access(
        user_id: int,
        project_id: int,
        db: AsyncSession,
        min_role: RoleEnum = RoleEnum.CONTRIBUTOR
    ) -> bool:
        """Verify user has access to project"""
        from app.models import ProjectMember

        # Check if user is admin (admins can access everything)
        is_admin = await RBACService.check_user_role(
            user_id,
            [RoleEnum.ADMIN],
            db
        )
        if is_admin:
            return True

        # Check project membership
        query = select(ProjectMember).where(
            (ProjectMember.project_id == project_id) &
            (ProjectMember.user_id == user_id)
        )
        result = await db.execute(query)
        member = result.scalar_one_or_none()

        return member is not None

    @staticmethod
    async def verify_team_access(
        user_id: int,
        team_id: int,
        db: AsyncSession
    ) -> bool:
        """Verify user has access to team"""
        from app.models import Team, TeamMember

        # Check if user is admin
        is_admin = await RBACService.check_user_role(
            user_id,
            [RoleEnum.ADMIN],
            db
        )
        if is_admin:
            return True

        # Check if user is team member or owner
        query = select(Team).where(
            (Team.id == team_id) & (Team.owner_id == user_id)
        )
        result = await db.execute(query)
        if result.scalar_one_or_none():
            return True

        query = select(TeamMember).where(
            (TeamMember.team_id == team_id) &
            (TeamMember.user_id == user_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None
