"""Scores descriptifs de couverture médiatique, jamais d'intention de vote."""
import math
from collections.abc import Iterable


def calculate_visibility_score(news_count: int, youtube_views: int, youtube_engagement: int,
                               publication_count: int, maxima: dict, weights: dict | None = None) -> float:
    weights = weights or {"news": .35, "views": .30, "engagement": .15, "frequency": .20}
    values = {"news": news_count, "views": youtube_views,
              "engagement": youtube_engagement, "frequency": publication_count}
    score = sum(weights[k] * min(1.0, max(0, values[k]) / maxima[k])
                for k in values if maxima.get(k, 0) > 0)
    return round(min(100.0, max(0.0, score * 100)), 2)


def calculate_ccr_relevance_score(content_ages: Iterable[float], distinct_topics: int,
                                  total_topics: int, volume_target: int = 10,
                                  half_life_days: int = 7, weights: dict | None = None) -> float:
    """Les âges concernent uniquement les contenus présentant un thème CCR."""
    ages = list(content_ages)
    if not ages:
        return 0.0
    weights = weights or {"volume": .5, "diversity": .3, "recency": .2}
    volume = min(1.0, len(ages) / volume_target)
    diversity = min(1.0, distinct_topics / max(total_topics, 1))
    recency = sum(math.pow(2, -max(0, age) / half_life_days) for age in ages) / len(ages)
    return round(min(100.0, max(0.0, 100 * (weights["volume"] * volume +
                       weights["diversity"] * diversity + weights["recency"] * recency))), 2)


def trend_from_delta(delta: float, threshold: float = 2) -> str:
    return "UP" if delta > threshold else "DOWN" if delta < -threshold else "STABLE"
