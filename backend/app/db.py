from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
from app.config import DATABASE_URL, SYNC_DATABASE_URL

# Async database engine & session
async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False}
)

async_session_maker = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Synchronous engine & session for fast bulk data ingestion
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)

sync_session_maker = sessionmaker(
    bind=sync_engine,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db_session():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
