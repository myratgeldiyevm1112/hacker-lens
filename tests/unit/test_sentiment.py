"""Unit tests for the VADER-based sentiment analyzer."""

import pytest

from hackerlens.nlp.sentiment import analyze_sentiment


def test_positive_text_returns_positive_score():
    score = analyze_sentiment("This is absolutely wonderful and amazing news!")
    assert score > 0.5


def test_negative_text_returns_negative_score():
    score = analyze_sentiment("This is terrible, awful, and a complete disaster.")
    assert score < -0.5


def test_neutral_text_returns_score_near_zero():
    score = analyze_sentiment("The meeting is scheduled for 3pm on Tuesday.")
    assert -0.2 <= score <= 0.2


@pytest.mark.parametrize("empty_text", [None, "", "   "])
def test_empty_or_missing_text_returns_none(empty_text):
    assert analyze_sentiment(empty_text) is None