import asyncio
import time

from redis.asyncio import Redis

_TOKEN_BUCKET_SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

local bucket = redis.call("HMGET", key, "tokens", "timestamp")
local tokens = tonumber(bucket[1])
local timestamp = tonumber(bucket[2])

if tokens == nil then
    tokens = capacity
    timestamp = now
end

local elapsed = math.max(0, now - timestamp)
tokens = math.min(capacity, tokens + elapsed * refill_rate)

local allowed = 0
if tokens >= requested then
    tokens = tokens - requested
    allowed = 1
end

redis.call("HMSET", key, "tokens", tokens, "timestamp", now)
redis.call("EXPIRE", key, math.ceil(capacity / refill_rate) + 1)

return {allowed, tokens}
"""


class TokenBucketRateLimiter:
    """
    Rate limiter for a named resource (e.g. "hn_api"), shared across
    any process pointed at the same Redis instance.

    Args:
        capacity: maximum burst size (tokens held when the bucket is full).
        refill_rate: tokens regenerated per second.
    """

    def __init__(
        self,
        redis: Redis,
        key: str,
        capacity: int = 10,
        refill_rate: float = 5.0,
    ) -> None:
        self._redis = redis
        self._key = f"ratelimit:{key}"
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._script = redis.register_script(_TOKEN_BUCKET_SCRIPT)

    async def acquire(self, tokens: int = 1) -> None:
        """Block until `tokens` are available, then consume them."""
        while True:
            allowed, _remaining = await self._script(
                keys=[self._key],
                args=[self._capacity, self._refill_rate, time.time(), tokens],
            )
            if allowed:
                return
            # Not enough tokens yet — wait roughly as long as it takes
            # for one token to regenerate, then check again.
            await asyncio.sleep(1 / self._refill_rate)