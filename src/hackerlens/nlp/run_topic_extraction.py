"""
Batch entry point: fits an LDA topic model over all currently stored
story titles and persists the resulting topics and item-topic links.

Run manually (not part of the per-item scrape pipeline) since topic
modeling needs to see the whole corpus at once, unlike sentiment
analysis which scores one item at a time.
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hackerlens.core.logging import logger
from hackerlens.db.models import Item, ItemTopic, ItemType, Topic
from hackerlens.db.session import async_session_factory
from hackerlens.nlp.topics import fit_topic_model


async def run_topic_extraction(session: AsyncSession, n_topics: int = 8) -> None:
    """Fit LDA over all stored story titles and persist topics + links."""
    stmt = select(Item.id, Item.title).where(Item.type == ItemType.STORY, Item.title.is_not(None))
    rows = (await session.execute(stmt)).all()

    item_ids = [row.id for row in rows]
    texts = [row.title for row in rows]
    logger.info(f"Running topic extraction over {len(texts)} story titles")

    result = fit_topic_model(texts, n_topics=n_topics)

    # Clear any previous run's topics so re-running this script doesn't
    # accumulate duplicate topic sets over time.
    await session.execute(ItemTopic.__table__.delete())
    await session.execute(Topic.__table__.delete())

    topic_rows = [
        Topic(label=", ".join(keywords[:3]), top_keywords=", ".join(keywords))
        for keywords in result.topic_keywords
    ]
    session.add_all(topic_rows)
    await session.flush()  # assign topic ids before creating links

    links = []
    for item_id, weights in zip(item_ids, result.doc_topic_weights):
        for topic_index, weight in enumerate(weights):
            if weight >= 0.1:  # skip negligible topic associations
                links.append(
                    ItemTopic(item_id=item_id, topic_id=topic_rows[topic_index].id, weight=weight)
                )
    session.add_all(links)
    await session.commit()

    logger.info(f"Saved {len(topic_rows)} topics and {len(links)} item-topic links")


async def main() -> None:
    async with async_session_factory() as session:
        await run_topic_extraction(session, n_topics=8)


if __name__ == "__main__":
    asyncio.run(main())