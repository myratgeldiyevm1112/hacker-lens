from unittest.mock import AsyncMock, MagicMock

import pytest

from hackerlens.scraper.rate_limiter import TokenBucketRateLimiter


def make_limiter(script_results: list[tuple[int, float]]) -> TokenBucketRateLimiter:
    """Build a limiter whose underlying Lua script call returns a
    pre-scripted sequence of (allowed, remaining_tokens) results."""
    fake_redis = MagicMock()
    fake_script = AsyncMock(side_effect=script_results)
    fake_redis.register_script.return_value = fake_script
    return TokenBucketRateLimiter(fake_redis, key="test", capacity=5, refill_rate=2.0)


@pytest.mark.asyncio
async def test_acquire_succeeds_immediately_when_tokens_available():
    limiter = make_limiter([(1, 4.0)])  # allowed on first try

    await limiter.acquire()  # should return without raising or looping

    limiter._script.assert_awaited_once()


@pytest.mark.asyncio
async def test_acquire_retries_until_tokens_available(monkeypatch):
    # First call: denied. Second call: allowed.
    limiter = make_limiter([(0, 0.0), (1, 1.0)])

    sleep_calls = []
    monkeypatch.setattr(
        "hackerlens.scraper.rate_limiter.asyncio.sleep",
        AsyncMock(side_effect=lambda s: sleep_calls.append(s)),
    )

    await limiter.acquire()

    assert limiter._script.await_count == 2
    assert sleep_calls == [0.5]  # 1 / refill_rate (2.0)