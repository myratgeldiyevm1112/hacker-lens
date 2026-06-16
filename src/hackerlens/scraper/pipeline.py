"""
The scrape -> clean -> save pipeline: fetches stories (and their
authors) from Hacker News, validates them through the Pydantic
schemas, and upserts them into Postgres.

Deduplication is handled at the database level via `INSERT ...
ON CONFLICT DO UPDATE` (a Postgres upsert), which is atomic and
therefore safe even if multiple pipeline runs overlap, unlike a
"check if exists, then insert" approach done from Python.
"""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from hackerlens.core.logging import logger
from hackerlens.core.schemas import AuthorCreate, ItemCreate
from hackerlens.db.models import Author, Item
from hackerlens.scraper.hn_client import HackerNewsClient


async def _upsert_item(session: AsyncSession, validated: ItemCreate) -> None:
    """Insert a new item, or update its mutable fields if it already exists."""
    values = validated.model_dump()
    stmt = pg_insert(Item).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Item.id],
        set_={
            "score": stmt.excluded.score,
            "num_comments": stmt.excluded.num_comments,
            "deleted": stmt.excluded.deleted,
            "dead": stmt.excluded.dead,
        },
    )
    await session.execute(stmt)


async def _ensure_author(session: AsyncSession, client: HackerNewsClient, username: str) -> None:
    """
    Insert an author if we haven't seen them before. We only fetch
    full profile info (karma, about, etc.) for authors not already
    in our database, to avoid one extra HN API call per item.
    """
    existing = await session.get(Author, username)
    if existing is not None:
        return

    raw_user = await client.get_user(username)
    if raw_user is None:
        return

    validated = AuthorCreate(id=raw_user["username"], **{
        k: v for k, v in raw_user.items() if k != "username"
    })
    stmt = pg_insert(Author).values(**validated.model_dump(by_alias=False))
    stmt = stmt.on_conflict_do_nothing(index_elements=[Author.username])
    await session.execute(stmt)


async def run_pipeline(
    session: AsyncSession,
    client: HackerNewsClient,
    feed: str = "top",
    limit: int = 100,
) -> int:
    """
    Run one full scrape -> clean -> save cycle for a given feed.

    Returns the number of items successfully persisted.
    """
    logger.info(f"Starting pipeline run for feed='{feed}', limit={limit}")
    raw_stories = await client.get_stories(feed=feed, limit=limit)

    saved_count = 0
    for raw in raw_stories:
        try:
            validated = ItemCreate(feed_type=feed, **raw)
        except Exception as exc:
            logger.warning(f"Skipping invalid item {raw.get('id')}: {exc}")
            continue

        if validated.by is not None:
            await _ensure_author(session, client, validated.by)

        await _upsert_item(session, validated)
        saved_count += 1

    await session.commit()
    logger.info(f"Pipeline run complete: saved {saved_count}/{len(raw_stories)} items")
    return saved_count