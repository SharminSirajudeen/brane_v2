"""
Database Connection and Session Management
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
import logging

from core.config import get_settings
from db.models import Base

logger = logging.getLogger(__name__)
settings = get_settings()

# Handle different database drivers
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite uses aiosqlite driver
    DATABASE_URL = settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
    engine_kwargs = {
        "echo": settings.DEBUG,
        "connect_args": {"check_same_thread": False},  # SQLite specific
    }
elif settings.DATABASE_URL.startswith("postgresql"):
    # PostgreSQL uses asyncpg driver
    DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine_kwargs = {
        "echo": settings.DEBUG,
        "poolclass": NullPool if settings.ENVIRONMENT == "test" else None,
        "pool_pre_ping": True,
    }
else:
    # Default fallback
    DATABASE_URL = settings.DATABASE_URL
    engine_kwargs = {"echo": settings.DEBUG}

# Create async engine
engine = create_async_engine(DATABASE_URL, **engine_kwargs)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initialize database (create tables)"""
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")


async def drop_db():
    """Drop all tables (for testing)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("Database tables dropped")


@asynccontextmanager
async def get_db():
    """
    Dependency for getting database session.
    Usage:
        async with get_db() as db:
            result = await db.execute(...)
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# FastAPI dependency
async def get_db_session() -> AsyncSession:
    """
    FastAPI dependency for route handlers.
    Usage:
        @app.get("/")
        async def route(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with get_db() as session:
        yield session
