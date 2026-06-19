import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hackerlens.db.base import Base


class ItemType(str, enum.Enum):
    """Mirrors the "type" field returned by the Hacker News API."""

    STORY = "story"
    COMMENT = "comment"
    JOB = "job"
    POLL = "poll"
    POLLOPT = "pollopt"


class FeedType(str, enum.Enum):
    """
    Which HN listing a story was discovered through. Set once when
    the scraper first fetches the story; we only record the feed it
    was first seen on, even if it later appears on others too.
    """

    TOP = "top"
    NEW = "new"
    BEST = "best"
    ASK = "ask"
    SHOW = "show"
    JOB = "job"


class Author(Base):
    """A Hacker News user, identified by their username."""

    __tablename__ = "authors"

    username: Mapped[str] = mapped_column(String(64), primary_key=True)
    karma: Mapped[int | None] = mapped_column(Integer, nullable=True)
    about: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    items: Mapped[list["Item"]] = relationship(back_populates="author")


class Item(Base):
    """
    A single Hacker News item: a story, comment, job posting, or poll.
    One table for all item types mirrors how HN itself models data
    and avoids duplicating near-identical columns across separate
    Post/Comment tables.
    """

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    type: Mapped[ItemType] = mapped_column(Enum(ItemType), nullable=False)

    by: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("authors.username"), nullable=True
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)

    score: Mapped[int] = mapped_column(Integer, default=0)
    num_comments: Mapped[int] = mapped_column(Integer, default=0)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("items.id"), nullable=True
    )
    feed_type: Mapped[FeedType | None] = mapped_column(Enum(FeedType), nullable=True)

    created_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    dead: Mapped[bool] = mapped_column(Boolean, default=False)

    author: Mapped["Author | None"] = relationship(back_populates="items")
    parent: Mapped["Item | None"] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list["Item"]] = relationship(back_populates="parent")

class Topic(Base):
    """
    A topic discovered by LDA over a batch of items. The label is a
    short, human-readable summary built from the topic's top
    keywords (e.g. "ai, model, training") since LDA itself doesn't
    name topics — only ranks word probabilities per topic.
    """

    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    top_keywords: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    items: Mapped[list["ItemTopic"]] = relationship(back_populates="topic")


class ItemTopic(Base):
    """
    Many-to-many link between items and topics, weighted by LDA's
    per-document topic probability. An item can belong to multiple
    topics with different weights, since LDA produces a probability
    distribution rather than a single hard label.
    """

    __tablename__ = "item_topics"

    item_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("items.id"), primary_key=True)
    topic_id: Mapped[int] = mapped_column(Integer, ForeignKey("topics.id"), primary_key=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False)

    item: Mapped["Item"] = relationship()
    topic: Mapped["Topic"] = relationship(back_populates="items")