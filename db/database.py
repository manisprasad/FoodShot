from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import config

engine = create_async_engine(
    config.DATABASE_URL, echo=False, pool_size=20, max_overflow=10, pool_pre_ping=True
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
