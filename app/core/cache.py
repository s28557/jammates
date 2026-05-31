import json
import logging
from typing import Any
import redis.asyncio as redis
from app.core.config import settings
logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis | None:
    """
    Returns a shared Redis client or None if Redis is not configured
    """
    global _redis_client

    if not settings.REDIS_URL:
        return None

    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    return _redis_client


async def cache_get(key: str) -> Any | None:
    """
    Reads a JSON value from Redis
    Returns None on cache miss or Redis errors
    """
    try:
        client = await get_redis()
        if client is None:
            return None

        value = await client.get(key)
        if value is None:
            return None

        return json.loads(value)
    except Exception as e:
        logger.error(f"Redis cache_get error for key {key}: {e}")
        return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 3600) -> None:
    """
    Stores a JSON value in Redis
    Fails silently so cache never breaks requests
    """
    try:
        client = await get_redis()
        if client is None:
            return

        await client.setex(
            key,
            ttl_seconds,
            json.dumps(value, ensure_ascii=False),
        )
    except Exception as e:
        logger.error(f"Redis cache_set error for key {key}: {e}")


async def cache_delete(key: str) -> None:
    """
    Deletes a Redis key
    Fails silently so cache never breaks requests
    """
    try:
        client = await get_redis()
        if client is None:
            return

        await client.delete(key)
    except Exception as e:
        logger.error(f"Redis cache_delete error for key {key}: {e}")
