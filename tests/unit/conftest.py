from unittest.mock import AsyncMock

import pytest

from hackerlens.scraper.hn_client import HackerNewsClient

SAMPLE_STORY = {
    "id": 1,
    "type": "story",
    "by": "testuser",
    "title": "Sample story",
    "url": "https://example.com",
    "score": 100,
    "descendants": 5,
    "time": 1700000000,
    "kids": [2, 3],
}

SAMPLE_COMMENT = {
    "id": 2,
    "type": "comment",
    "by": "commenter",
    "text": "Nice post!",
    "parent": 1,
    "time": 1700000100,
}


@pytest.fixture
def mock_hn_client() -> HackerNewsClient:
    client = HackerNewsClient()
    client._request = AsyncMock()
    return client