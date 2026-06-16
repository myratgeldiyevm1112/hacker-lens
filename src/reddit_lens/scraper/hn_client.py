"""
Async client for the public Hacker News API (Firebase-based).
Docs: https://github.com/HackerNews/API
No authentication is required.
"""

from datetime import datetime

import httpx

from reddit_lens.core.config import settings

VALID_FEEDS = {"top", "new", "best", "ask", "show", "job"}


class HackerNewsClient:
    """
    Thin async wrapper around the public Hacker News API.

    Keeps all direct HTTP calls to HN in one place so the rest of
    the app depends on this interface, not on the raw API shape
    (makes it easy to mock in tests or swap data sources later).
    """

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or settings.hn_base_url
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=10.0)

    async def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        await self._client.aclose()

    async def get_item(self, item_id: int) -> dict | None:
        """
        Fetch a single item (story, comment, job, or poll) by id.
        Returns None if the item does not exist or was deleted.
        """
        response = await self._client.get(f"/v0/item/{item_id}.json")
        response.raise_for_status()
        data = response.json()
        return self._serialize_item(data) if data else None

    async def get_story_ids(self, feed: str = "top", limit: int = 100) -> list[int]:
        """
        Fetch the current list of story ids for a given feed.

        Args:
            feed: one of "top", "new", "best", "ask", "show", "job".
            limit: maximum number of ids to return.
        """
        if feed not in VALID_FEEDS:
            raise ValueError(f"Unknown feed '{feed}', expected one of {VALID_FEEDS}")

        response = await self._client.get(f"/v0/{feed}stories.json")
        response.raise_for_status()
        all_ids: list[int] = response.json()
        return all_ids[:limit]

    async def get_stories(self, feed: str = "top", limit: int = 100) -> list[dict]:
        """
        Fetch full story items for a given feed.

        Note: this fetches items one by one. Phase 2 will replace
        this with concurrent fetching for better throughput.
        """
        story_ids = await self.get_story_ids(feed, limit)
        stories = []
        for story_id in story_ids:
            item = await self.get_item(story_id)
            if item is not None and item["type"] == "story":
                stories.append(item)
        return stories

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
        response = await self._client.get(f"/v0/user/{username}.json")
        response.raise_for_status()
        data = response.json()
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