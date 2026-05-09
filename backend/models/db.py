# See: specs/backend/upsert-endpoint.md — Database Models
import os
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_optimizer",
)

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


class CacheEntry(Base):
    __tablename__ = "cache_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    team_id = Column(String(255), nullable=True, index=True)
    query_hash = Column(String(64), nullable=False, unique=True, index=True)
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    tokens_saved = Column(Integer, default=0)
    model_used = Column(String(100), default="gpt-4.1-mini")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    team_id = Column(String(255), nullable=True, index=True)
    query_hash = Column(String(64), nullable=False)
    cache_hit = Column(Boolean, default=False)
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


async def get_db():
    """FastAPI dependency: yields an async SQLAlchemy session."""
    async with AsyncSessionLocal() as session:
        yield session
