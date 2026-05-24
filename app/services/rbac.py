"""RBAC helpers used inside route handlers when permissions depend on resource state
(e.g. only the team owner can edit the team)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ProjectMember,
    Role,
    RoleEnum,
    Team,
    TeamMember,
    User,
)


class RBACService:

    @staticmethod
    async def get_user_role_name(user_id: int, db: AsyncSession) -> str | None:
        result = await db.execute(
            select(Role.name)
            .join(User, User.role_id == Role.id)
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def user_has_role(
        user_id: int,
        allowed: list[RoleEnum | str],
        db: AsyncSession,
    ) -> bool:
        role_name = await RBACService.get_user_role_name(user_id, db)
        if role_name is None:
            return False
        allowed_names = {r.value if isinstance(r, RoleEnum) else r for r in allowed}
        return role_name in allowed_names

    @staticmethod
    async def is_admin(user_id: int, db: AsyncSession) -> bool:
        return await RBACService.user_has_role(user_id, [RoleEnum.ADMIN], db)

    @staticmethod
    async def has_team_access(user_id: int, team_id: int, db: AsyncSession) -> bool:
        """True if user is admin, team owner, or a team member."""
        if await RBACService.is_admin(user_id, db):
            return True

        team = (await db.execute(
            select(Team).where(Team.id == team_id)
        )).scalar_one_or_none()
        if not team:
            return False
        if team.owner_id == user_id:
            return True

        member = (await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
        )).scalar_one_or_none()
        return member is not None

    @staticmethod
    async def has_project_access(user_id: int, project_id: int, db: AsyncSession) -> bool:
        if await RBACService.is_admin(user_id, db):
            return True
        member = (await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )).scalar_one_or_none()
        return member is not None

    @staticmethod
    async def is_project_admin(user_id: int, project_id: int, db: AsyncSession) -> bool:
        """True if user is app-admin or has the 'admin' role on the project."""
        if await RBACService.is_admin(user_id, db):
            return True
        member = (await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )).scalar_one_or_none()
        return member is not None and member.role == "admin"
