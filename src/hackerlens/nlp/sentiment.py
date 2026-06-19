"""
Sentiment analysis via VADER (Valence Aware Dictionary and sEntiment
Reasoner). VADER is lexicon-based and tuned for short, informal text
(social media posts, headlines) rather than long-form prose, which
fits HN titles and comments well.
"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()


def analyze_sentiment(text: str | None) -> float | None:
    """
    Return VADER's compound sentiment score for a piece of text,
    ranging from -1.0 (most negative) to +1.0 (most positive).

    Returns None for empty or missing text, since "no sentiment"
    is different from "neutral sentiment" (score 0.0).
    """
    if not text or not text.strip():
        return None
    return _analyzer.polarity_scores(text)["compound"]