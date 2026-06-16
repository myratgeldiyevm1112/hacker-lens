"""
Async client for the public Hacker News API (Firebase-based).
Docs: https://github.com/HackerNews/API
No authentication is required.
"""
import asyncio
from datetime import datetime

import httpx

from hackerlens.core.config import settings
from hackerlens.scraper.rate_limiter import TokenBucketRateLimiter
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from hackerlens.core.logging import logger

VALID_FEEDS = {"top", "new", "best", "ask", "show", "job"}


class HackerNewsClient:
    """
    Thin async wrapper around the public Hacker News API.

    Keeps all direct HTTP calls to HN in one place so the rest of
    the app depends on this interface, not on the raw API shape
    (makes it easy to mock in tests or swap data sources later).
    """

    def __init__(
        self,
        base_url: str | None = None,
        rate_limiter: TokenBucketRateLimiter | None = None,
    ) -> None:
        self._base_url = base_url or settings.hn_base_url
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=10.0)
        self._rate_limiter = rate_limiter

    async def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        await self._client.aclose()

    async def get_item(self, item_id: int) -> dict | None:
        """
        Fetch a single item (story, comment, job, or poll) by id.
        Returns None if the item does not exist or was deleted.
        """
        if self._rate_limiter is not None:
            await self._rate_limiter.acquire()
        data = await self._request(f"/v0/item/{item_id}.json")
        return self._serialize_item(data) if data else None

    @retry(
        retry=retry_if_exception_type(httpx.TransportError | httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    async def _request(self, path: str) -> dict | list | None:
        """
        Perform a single GET request against the HN API with retry
        and exponential backoff on transient network errors or 5xx
        responses. 4xx errors (bad request) are not retried — they
        won't succeed on a second attempt.
        """
        try:
            response = await self._client.get(path)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code < 500:
                raise  # client error, retrying won't help
            logger.warning(f"Transient error on {path}: {exc}. Retrying...")
            raise
        except httpx.TransportError as exc:
            logger.warning(f"Network error on {path}: {exc}. Retrying...")
            raise

    async def get_story_ids(self, feed: str = "top", limit: int = 100) -> list[int]:
        """
        Fetch the current list of story ids for a given feed.

        Args:
            feed: one of "top", "new", "best", "ask", "show", "job".
            limit: maximum number of ids to return.
        """
        if feed not in VALID_FEEDS:
            raise ValueError(f"Unknown feed '{feed}', expected one of {VALID_FEEDS}")

        all_ids: list[int] = await self._request(f"/v0/{feed}stories.json")
        return all_ids[:limit]

    async def get_stories(
        self, feed: str = "top", limit: int = 100, max_concurrency: int = 10
    ) -> list[dict]:
        """
        Fetch full story items for a given feed, concurrently.

        Args:
            feed: one of "top", "new", "best", "ask", "show", "job".
            limit: maximum number of stories to return.
            max_concurrency: maximum number of in-flight requests to
                HN at once. Caps how aggressively we hit a free,
                shared public API.
        """
        story_ids = await self.get_story_ids(feed, limit)
        semaphore = asyncio.Semaphore(max_concurrency)

        async def fetch_with_limit(item_id: int) -> dict | None:
            async with semaphore:
                return await self.get_item(item_id)

        items = await asyncio.gather(*(fetch_with_limit(sid) for sid in story_ids))
        return [item for item in items if item is not None and item["type"] == "story"]

    async def get_comments(self, item_id: int, depth: int = 1) -> list[dict]:
        """
        Fetch comments attached to an item (story or comment) up to
        a given nesting depth.

        Args:
            item_id: id of the parent story or comment.
            depth: how many levels of replies to include.
                   depth=1 means top-level comments only.
        """
        comments: list[dict] = []
        await self._collect_comments(item_id, comments, current_depth=1, max_depth=depth)
        return comments

    async def get_user(self, username: str) -> dict | None:
        """Fetch basic profile info for a Hacker News user."""
        data = await self._request(f"/v0/user/{username}.json")
        if data is None:
            return None
        return {
            "username": data.get("id"),
            "karma": data.get("karma"),
            "about": data.get("about"),
            "created_utc": datetime.fromtimestamp(data["created"]),
        }

    async def _collect_comments(
        self,
        parent_id: int,
        accumulator: list[dict],
        current_depth: int,
        max_depth: int,
    ) -> None:
        """Recursively walk the comment tree via "kids" ids, up to max_depth."""
        parent = await self.get_item(parent_id)
        if parent is None or "kids" not in parent:
            return

        for kid_id in parent["kids"]:
            comment = await self.get_item(kid_id)
            if comment is None or comment.get("deleted") or comment.get("dead"):
                continue
            accumulator.append(comment)
            if current_depth < max_depth:
                await self._collect_comments(kid_id, accumulator, current_depth + 1, max_depth)

    @staticmethod
    def _serialize_item(data: dict) -> dict:
        """Normalize a raw HN item into a flat dict with consistent fields."""
        return {
            "id": data["id"],
            "type": data.get("type"),
            "by": data.get("by", "[deleted]"),
            "title": data.get("title"),
            "text": data.get("text"),
            "url": data.get("url"),
            "score": data.get("score", 0),
            "num_comments": data.get("descendants", 0),
            "created_utc": datetime.fromtimestamp(data["time"]) if "time" in data else None,
            "kids": data.get("kids", []),
        }