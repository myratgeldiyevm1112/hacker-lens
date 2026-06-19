"""
Read-side aggregation queries over already-persisted data. Kept
separate from the scraper/nlp modules (which produce data) since
this module only consumes it — these queries will back the
analytics endpoints added in Phase 4.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hackerlens.db.models import Item


async def sentiment_by_feed(session: AsyncSession) -> list[dict]:
    """
    Average sentiment score and item count, grouped by feed_type.
    Items without a sentiment score (e.g. comments with empty text)
    are excluded from the average via the WHERE clause.
    """
    stmt = (
        select(
            Item.feed_type,
            func.avg(Item.sentiment_score).label("avg_sentiment"),
            func.count(Item.id).label("item_count"),
        )
        .where(Item.sentiment_score.is_not(None))
        .group_by(Item.feed_type)
        .order_by(Item.feed_type)
    )
    result = await session.execute(stmt)
    return [
        {"feed_type": row.feed_type, "avg_sentiment": row.avg_sentiment, "item_count": row.item_count}
        for row in result
    ]


async def sentiment_over_time(session: AsyncSession, bucket: str = "day") -> list[dict]:
    """
    Average sentiment score over time, bucketed by hour or day.

    Args:
        bucket: "hour" or "day" — uses Postgres's date_trunc to group
            timestamps into fixed-size buckets.
    """
    if bucket not in ("hour", "day"):
        raise ValueError(f"Unsupported bucket '{bucket}', expected 'hour' or 'day'")

    time_bucket = func.date_trunc(bucket, Item.created_utc).label("time_bucket")
    stmt = (
        select(
            time_bucket,
            func.avg(Item.sentiment_score).label("avg_sentiment"),
            func.count(Item.id).label("item_count"),
        )
        .where(Item.sentiment_score.is_not(None))
        .group_by(time_bucket)
        .order_by(time_bucket)
    )
    result = await session.execute(stmt)
    return [
        {"time_bucket": row.time_bucket, "avg_sentiment": row.avg_sentiment, "item_count": row.item_count}
        for row in result
    ]

