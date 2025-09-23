"""
Database connection management.
"""

import asyncio
from typing import Optional

import redis.asyncio as redis
from elasticsearch import AsyncElasticsearch
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# SQLAlchemy setup
engine = create_async_engine(
    settings.POSTGRES_URL,
    echo=settings.ENVIRONMENT == "development",
    pool_pre_ping=True,
    pool_recycle=300,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

# MongoDB client
mongodb_client: Optional[AsyncIOMotorClient] = None
mongodb_db = None

# Redis client
redis_client: Optional[redis.Redis] = None

# Elasticsearch client
elasticsearch_client: Optional[AsyncElasticsearch] = None


async def get_postgres_session() -> AsyncSession:
    """Get PostgreSQL async session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_mongodb_db():
    """Get MongoDB database."""
    return mongodb_db


def get_redis_client():
    """Get Redis client."""
    return redis_client


def get_elasticsearch_client():
    """Get Elasticsearch client."""
    return elasticsearch_client


async def init_databases():
    """Initialize all database connections."""
    global mongodb_client, mongodb_db, redis_client, elasticsearch_client

    # MongoDB
    mongodb_client = AsyncIOMotorClient(settings.MONGODB_URL)
    mongodb_db = mongodb_client.veracity

    # Redis
    redis_client = redis.from_url(settings.REDIS_URL)

    # Elasticsearch
    elasticsearch_client = AsyncElasticsearch([settings.ELASTICSEARCH_URL])

    # Test connections
    try:
        # Test MongoDB
        await mongodb_client.admin.command("ping")

        # Test Redis
        await redis_client.ping()

        # Test Elasticsearch
        await elasticsearch_client.ping()

        print("✅ All database connections established")

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise


async def close_databases():
    """Close all database connections."""
    global mongodb_client, redis_client, elasticsearch_client

    if mongodb_client:
        mongodb_client.close()

    if redis_client:
        await redis_client.close()

    if elasticsearch_client:
        await elasticsearch_client.close()

    if engine:
        await engine.dispose()

    print("✅ All database connections closed")
