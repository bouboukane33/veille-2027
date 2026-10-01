from datetime import date

import pytest

from src.database.models import Content
from src.database.repository import Repository
from src.processing.cleaner import clean_content
from src.processing.metrics import build_daily_metrics
from src.processing.topic_classifier import KeywordTopicClassifier


def article(config, url, title="Édouard Philippe et Gabriel Attal : climat et assurance"):
    return clean_content(Content("news", title, "Prévention", "Test RSS", url,
                         "2026-09-30T08:00:00Z", "2026-09-30T09:00:00Z"), config.followed)


def test_multimention_dedup_fuzzy_and_persistent_alias(config):
    with Repository(config.db_path(), config) as repo:
        repo.initialize()
        a = article(config, "https://example.org/a?utm_source=x")
        b = article(config, "https://example.org/b", a.title + ".")
        assert repo.save_contents([a, b]) == {"inserted": 1, "duplicates": 1}
        # Même URL lors d'une autre collecte : le titre peut changer sans créer un second article.
        b.title = "Nouveau titre totalement différent mentionnant Gabriel Attal"
        assert repo.save_contents([b]) == {"inserted": 0, "duplicates": 1}
        assert repo.connection.execute("SELECT COUNT(*) FROM news_articles").fetchone()[0] == 1
        repo.reclassify(KeywordTopicClassifier(config.topics))
        links = repo.connection.execute("SELECT personality_id FROM content_personalities").fetchall()
        assert {r[0] for r in links} == {"edouard_philippe", "gabriel_attal"}
        metrics = build_daily_metrics(repo, date(2026, 9, 30))
        for pid in ("edouard_philippe", "gabriel_attal"):
            today = next(r for r in metrics if r["personality_id"] == pid and r["date"] == "2026-09-30")
            assert today["news_count"] == 1
            assert today["topic_ccr_count"] == 1  # Trois thèmes ne deviennent pas trois contenus.
            assert today["visibility_score"] == 55  # Aucun YouTube : poids absents restent à zéro.


def test_video_upsert_updates_stats_and_preserves_unknown(config):
    c = clean_content(Content("youtube", "Gabriel Attal — climat", "", "Test",
        "https://www.youtube.com/watch?v=abc", "2026-09-30T08:00:00Z", "2026-09-30T09:00:00Z",
        video_id="abc", view_count=100, like_count=5), config.followed)
    with Repository(config.db_path(), config) as repo:
        repo.initialize()
        repo.save_contents([c])
        c.view_count, c.like_count = 200, None
        repo.save_contents([c])
        row = repo.connection.execute("SELECT * FROM youtube_videos").fetchone()
        assert row["view_count"] == 200
        assert row["like_count"] == 5
        assert row["comment_count"] is None
        assert repo.connection.execute("SELECT COUNT(*) FROM youtube_videos").fetchone()[0] == 1


def test_demo_live_mix_is_refused(config):
    with Repository(config.db_path(True), config, True) as repo:
        repo.initialize()
        with pytest.raises(ValueError, match="incompatible"):
            repo.save_contents([article(config, "https://example.org/a")])
    with Repository(config.db_path(True), config, False) as repo:
        with pytest.raises(ValueError, match="Mélange"):
            repo.initialize()
