from redis.asyncio import Redis

from hackerlens.core.config import settings


def get_redis_client() -> Redis:
    """Create an async Redis client from the configured REDIS_URL."""
    return Redis.from_url(settings.redis_url, decode_responses=True)