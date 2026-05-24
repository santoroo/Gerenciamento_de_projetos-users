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
    """Create all tables. Safe to call at startup."""
    # Ensure model classes are registered with Base.metadata before create_all.
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    """Drop all tables. Destructive — use with caution."""
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
