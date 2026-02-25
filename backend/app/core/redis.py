import redis.asyncio as redis

from app.core.config import settings

pool = redis.ConnectionPool.from_url(
    settings.redis_url,
    max_connections=50,
    decode_responses=True,
    socket_timeout=5,
    socket_connect_timeout=5,
    retry_on_timeout=True,
)

redis_client = redis.Redis(connection_pool=pool)
