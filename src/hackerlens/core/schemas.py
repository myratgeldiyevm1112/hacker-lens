from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from hackerlens.db.models import FeedType, ItemType


class ItemCreate(BaseModel):
    """
    Validates a single raw item as received from the Hacker News API
    before it gets persisted to the database.
    """

    id: int
    type: ItemType
    by: str | None = None
    title: str | None = None
    text: str | None = None
    url: str | None = None
    score: int = 0
    num_comments: int = Field(default=0, alias="descendants")
    parent_id: int | None = Field(default=None, alias="parent")
    feed_type: FeedType | None = None
    created_utc: datetime | None = None
    deleted: bool = False
    dead: bool = False
    sentiment_score: float | None = None

    model_config = ConfigDict(populate_by_name=True)


class ItemResponse(BaseModel):
    """What our own API returns for a single item (Phase 4)."""

    id: int
    type: ItemType
    by: str | None
    title: str | None
    text: str | None
    url: str | None
    score: int
    num_comments: int
    parent_id: int | None
    feed_type: FeedType | None
    created_utc: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AuthorCreate(BaseModel):
    """Validates a raw user profile as received from the Hacker News API."""

    username: str = Field(alias="id")
    karma: int | None = None
    about: str | None = None
    created_utc: datetime | None = Field(default=None, alias="created")

    model_config = ConfigDict(populate_by_name=True)


class AuthorResponse(BaseModel):
    """What our own API returns for a single author (Phase 4)."""

    username: str
    karma: int | None
    about: str | None
    created_utc: datetime | None

    model_config = ConfigDict(from_attributes=True)