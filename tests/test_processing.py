import math

import pytest

from src.processing.cleaner import canonical_url, clean_text, detect_personalities, iso_datetime, normalize_text
from src.processing.deduplicator import similar_article
from src.processing.scoring import calculate_ccr_relevance_score, calculate_visibility_score, trend_from_delta
from src.processing.topic_classifier import KeywordTopicClassifier


def test_cleaning_and_aliases(config):
    assert clean_text("<p>Climat &amp; assurance</p><script>secret()</script>") == "Climat & assurance"
    assert normalize_text("Jean-Luc Mélenchon") == "jean luc melenchon"
    matches = detect_personalities("Édouard Philippe rencontre Jean Luc Melenchon.", config.followed)
    assert set(matches) == {"edouard_philippe", "jean_luc_melenchon"}
    assert not detect_personalities("Gabriel Attalement", config.followed)


def test_topics_use_token_boundaries(config):
    classifier = KeywordTopicClassifier(config.topics)
    assert set(classifier.classify("RGA et inondations : adaptation climatique et réassurance")) == {
        "secheresse", "inondation", "climat", "assurance"}
    assert classifier.classify("une assurancevie et organisation") == {}


def test_canonical_url_keeps_article_identifiers():
    assert canonical_url("https://EXAMPLE.org/a?id=7&utm_source=mail#top") == "https://example.org/a?id=7"
    with pytest.raises(ValueError):
        canonical_url("javascript:alert(1)")
    assert iso_datetime("Wed, 30 Sep 2026 14:00:00 +0200") == "2026-09-30T12:00:00Z"


def test_fuzzy_dedup_is_conservative():
    a = "Gabriel Attal présente les mesures de prévention des inondations"
    b = "Gabriel Attal présente les mesures de prévention des inondations."
    assert similar_article(a, "2026-09-30T00:00:00Z", b, "2026-09-30T01:00:00Z")
    assert not similar_article(a, "2026-09-30T00:00:00Z", b, "2026-09-20T01:00:00Z")
    assert not similar_article(a + " 2026", "2026-09-30T00:00:00Z", b + " 2027", "2026-09-30T00:00:00Z")


def test_scores_reference_examples_and_bounds():
    maxima = {"news": 10, "views": 1000, "engagement": 100, "frequency": 20}
    assert calculate_visibility_score(10, 1000, 100, 20, maxima) == 100
    assert calculate_visibility_score(5, 500, 50, 10, maxima) == 50
    assert calculate_visibility_score(0, 0, 0, 0, dict.fromkeys(maxima, 0)) == 0
    assert calculate_visibility_score(-1, -5, -1, -1, maxima) == 0
    assert calculate_visibility_score(100, 2000, 1000, 40, maxima) == 100
    assert calculate_ccr_relevance_score([], 0, 10) == 0
    assert calculate_ccr_relevance_score([0] * 10, 10, 10) == 100
    assert calculate_ccr_relevance_score([7] * 10, 10, 10) == 90
    assert math.isclose(calculate_ccr_relevance_score([0], 1, 10), 28)


@pytest.mark.parametrize("delta,expected", [(3, "UP"), (2, "STABLE"), (0, "STABLE"), (-2, "STABLE"), (-3, "DOWN")])
def test_trend_threshold(delta, expected):
    assert trend_from_delta(delta) == expected
