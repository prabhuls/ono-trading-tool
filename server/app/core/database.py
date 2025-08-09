"""
Database configuration and session management using SQLAlchemy
"""
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy import MetaData, event, Pool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import settings
from app.core.logging import get_logger

# Create logger for this module
logger = get_logger(__name__)


# Naming convention for database constraints
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Base class for all database models"""
    metadata = metadata


# Create async engine only if database is enabled
engine: Optional[AsyncEngine] = None
async_session_maker: Optional[async_sessionmaker] = None

if settings.enable_database and settings.async_database_url:
    engine = create_async_engine(
        settings.async_database_url,
        echo=settings.database.echo,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
        pool_timeout=settings.database.pool_timeout,
        pool_recycle=settings.database.pool_recycle,
        pool_pre_ping=True,  # Enable connection health checks
        poolclass=NullPool if settings.is_testing else QueuePool,
    )

    # Create async session factory
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


# Database dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.
    
    Usage in FastAPI:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
    """
    if not settings.enable_database:
        raise RuntimeError("Database is not enabled. Set ENABLE_DATABASE=true to use database features.")
    
    if not async_session_maker:
        raise RuntimeError("Database is not properly configured. Check DATABASE_URL setting.")
    
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database session.
    
    Usage:
        async with get_db_context() as db:
            user = await db.get(User, user_id)
    """
    if not settings.enable_database:
        raise RuntimeError("Database is not enabled. Set ENABLE_DATABASE=true to use database features.")
    
    if not async_session_maker:
        raise RuntimeError("Database is not properly configured. Check DATABASE_URL setting.")
    
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class DatabaseManager:
    """Manager class for database operations"""
    
    @staticmethod
    async def create_all():
        """Create all tables"""
        if not settings.enable_database:
            logger.warning("Database is disabled. Skipping table creation.")
            return
            
        if not engine:
            raise RuntimeError("Database engine is not initialized")
            
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
    
    @staticmethod
    async def drop_all():
        """Drop all tables (use with caution!)"""
        if not settings.enable_database:
            logger.warning("Database is disabled. Skipping table drop.")
            return
            
        if not engine:
            raise RuntimeError("Database engine is not initialized")
            
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            logger.warning("All database tables dropped")
    
    @staticmethod
    async def check_connection() -> bool:
        """Check if database connection is healthy"""
        if not settings.enable_database:
            logger.info("Database is disabled")
            return False
            
        if not engine:
            logger.error("Database engine is not initialized")
            return False
            
        try:
            from sqlalchemy import text
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False
    
    @staticmethod
    async def close():
        """Close database connections"""
        if engine:
            await engine.dispose()
            logger.info("Database connections closed")
        else:
            logger.info("No database connections to close")


# Connection pool event listeners (only register if database is enabled)
if settings.enable_database and engine:
    @event.listens_for(Pool, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set SQLite pragmas for better performance (if using SQLite)"""
        if settings.database_url and settings.database_url.startswith("sqlite"):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()


    @event.listens_for(Pool, "checkout")
    def ping_connection(dbapi_connection, connection_record, connection_proxy):
        """Ping database connection to check if it's still valid"""
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("SELECT 1")
        except:
            # Connection is broken, let's reconnect
            raise


# Transaction decorator
def transactional(func):
    """
    Decorator to wrap function in database transaction.
    
    Usage:
        @transactional
        async def create_user_with_profile(db: AsyncSession, user_data, profile_data):
            user = User(**user_data)
            db.add(user)
            
            profile = Profile(**profile_data, user=user)
            db.add(profile)
            
            return user
    """
    async def wrapper(*args, **kwargs):
        if not settings.enable_database:
            raise RuntimeError("Database is not enabled. Cannot use @transactional decorator.")
            
        # Find the session in args or kwargs
        session = None
        for arg in args:
            if isinstance(arg, AsyncSession):
                session = arg
                break
        
        if not session and 'db' in kwargs:
            session = kwargs['db']
        
        if not session:
            # If no session provided, create one
            async with get_db_context() as db:
                return await func(*args, db=db, **kwargs)
        else:
            # Use existing session
            return await func(*args, **kwargs)
    
    return wrapper