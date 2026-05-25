from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings


def _engine_kwargs() -> dict:
    """Pool args only make sense for server databases (Postgres/MySQL).
    SQLite's aiosqlite driver doesn't accept pool_size / max_overflow."""
    kwargs = {
        "echo": settings.sqlalchemy_echo,
        "future": True,
    }
    if not settings.database_url.startswith("sqlite"):
        kwargs.update({"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20})
    return kwargs


engine = create_async_engine(settings.database_url, **_engine_kwargs())

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db():
    """FastAPI dependency that yields a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables and bootstrap default data. Safe to call at startup."""
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _bootstrap_defaults()


async def _bootstrap_defaults():
    """Ensure default roles exist and create admin user if no admin is present."""
    import logging
    from sqlalchemy import select, or_
    from app.models import Role, RoleEnum, User
    from app.utils.security import hash_password

    logger = logging.getLogger("app.bootstrap")

    async with AsyncSessionLocal() as session:
        for name, desc in (
            (RoleEnum.ADMIN.value, "Tech Lead / Arquiteto — acesso total"),
            (RoleEnum.MANAGER.value, "Gerente de Projetos — gerencia equipes e projetos"),
            (RoleEnum.CONTRIBUTOR.value, "Desenvolvedor — acesso limitado"),
        ):
            existing = (await session.execute(
                select(Role).where(Role.name == name)
            )).scalar_one_or_none()
            if not existing:
                session.add(Role(name=name, description=desc))
                logger.info("Role criada: %s", name)
        await session.commit()

        admin_role = (await session.execute(
            select(Role).where(Role.name == RoleEnum.ADMIN.value)
        )).scalar_one()

        has_admin = (await session.execute(
            select(User).where(User.role_id == admin_role.id)
        )).first()

        if not has_admin:
            conflict = (await session.execute(
                select(User).where(
                    or_(User.username == "admin_user", User.email == "admin@example.com")
                )
            )).scalar_one_or_none()
            if not conflict:
                session.add(User(
                    username="admin_user",
                    email="admin@example.com",
                    full_name="Administrador",
                    hashed_password=hash_password("password123"),
                    role_id=admin_role.id,
                    is_active=True,
                ))
                await session.commit()
                logger.info("Admin padrão criado: admin_user / password123")


async def drop_db():
    """Drop all tables. Destructive — use with caution."""
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
