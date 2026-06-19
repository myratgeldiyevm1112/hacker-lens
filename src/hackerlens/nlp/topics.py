"""
Topic extraction over a batch of item titles.

TF-IDF surfaces the most distinctive keywords overall (rare-but-
important terms). LDA finds latent topic clusters by modeling
co-occurrence patterns across documents. They serve different
purposes and, by convention, use different vectorizers: LDA is
typically fit on raw term counts (CountVectorizer) rather than
TF-IDF weights, since TF-IDF's weighting scheme conflicts with
LDA's own statistical assumptions about word distributions.
"""

from dataclasses import dataclass

from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer, ENGLISH_STOP_WORDS

from hackerlens.core.logging import logger

HN_STOP_WORDS = ["hn", "ask", "show", "new", "using", "use", "via"]

CUSTOM_STOP_WORDS = list(ENGLISH_STOP_WORDS) + HN_STOP_WORDS


def top_keywords_tfidf(texts: list[str], top_n: int = 20) -> list[tuple[str, float]]:
    """
    Return the top_n keywords across the whole corpus, ranked by
    summed TF-IDF score. Distinctive-but-frequent terms rank highest;
    very common English words are naturally suppressed by IDF.
    """
    vectorizer = TfidfVectorizer(stop_words=CUSTOM_STOP_WORDS, max_df=0.9, min_df=2)
    matrix = vectorizer.fit_transform(texts)
    scores = matrix.sum(axis=0).A1  # sum TF-IDF weight per term across all documents
    vocabulary = vectorizer.get_feature_names_out()

    ranked = sorted(zip(vocabulary, scores), key=lambda pair: pair[1], reverse=True)
    return ranked[:top_n]


@dataclass
class TopicModelResult:
    """
    Output of fitting an LDA model: per-topic top keywords, and
    each input document's probability distribution across topics.
    """

    topic_keywords: list[list[str]]  # one keyword list per topic
    doc_topic_weights: list[list[float]]  # one row per input document


def fit_topic_model(
    texts: list[str], n_topics: int = 8, top_keywords_per_topic: int = 10
) -> TopicModelResult:
    """
    Fit an LDA topic model over a list of documents.

    Args:
        texts: input documents (e.g. item titles).
        n_topics: number of latent topics to discover (5-10 is
            reasonable for a few hundred short HN titles).
        top_keywords_per_topic: how many top words to keep per topic
            label.
    """
    vectorizer = CountVectorizer(stop_words=CUSTOM_STOP_WORDS, max_df=0.7, min_df=2)
    doc_term_matrix = vectorizer.fit_transform(texts)
    vocabulary = vectorizer.get_feature_names_out()

    lda = LatentDirichletAllocation(n_components=n_topics, random_state=42, learning_method="batch")
    doc_topic_matrix = lda.fit_transform(doc_term_matrix)

    topic_keywords = []
    for topic_weights in lda.components_:
        top_indices = topic_weights.argsort()[: -top_keywords_per_topic - 1 : -1]
        topic_keywords.append([vocabulary[i] for i in top_indices])

    logger.info(f"Fit LDA with {n_topics} topics over {len(texts)} documents")
    return TopicModelResult(
        topic_keywords=topic_keywords,
        doc_topic_weights=doc_topic_matrix.tolist(),
    )