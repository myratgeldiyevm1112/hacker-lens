import pytest

from tests.unit.conftest import SAMPLE_STORY


@pytest.mark.asyncio
async def test_get_item_returns_serialized_story(mock_hn_client):
    mock_hn_client._request.return_value = SAMPLE_STORY

    result = await mock_hn_client.get_item(1)

    assert result["id"] == 1
    assert result["title"] == "Sample story"
    assert result["num_comments"] == 5  # renamed from "descendants"


@pytest.mark.asyncio
async def test_get_item_returns_none_for_missing_item(mock_hn_client):
    mock_hn_client._request.return_value = None

    result = await mock_hn_client.get_item(999)

    assert result is None


@pytest.mark.asyncio
async def test_get_story_ids_respects_limit(mock_hn_client):
    mock_hn_client._request.return_value = list(range(1, 101))  # 100 fake ids

    result = await mock_hn_client.get_story_ids(feed="top", limit=10)

    assert len(result) == 10
    assert result == list(range(1, 11))


@pytest.mark.asyncio
async def test_get_story_ids_rejects_unknown_feed(mock_hn_client):
    with pytest.raises(ValueError, match="Unknown feed"):
        await mock_hn_client.get_story_ids(feed="not_a_real_feed", limit=10)


@pytest.mark.asyncio
async def test_get_stories_filters_out_non_story_items(mock_hn_client):
    # First call returns ids, second+ calls return items via get_item.
    mock_hn_client._request.side_effect = [
        [1, 2],  # get_story_ids -> raw id list
        {"id": 1, "type": "story", "time": 1700000000},
        {"id": 2, "type": "comment", "time": 1700000000},  # should be filtered out
    ]

    result = await mock_hn_client.get_stories(feed="top", limit=2)

    assert len(result) == 1
    assert result[0]["id"] == 1