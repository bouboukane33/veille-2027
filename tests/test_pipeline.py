import json
from datetime import date, timedelta

import pandas as pd

from src.database.repository import Repository
from src.pipeline import run_pipeline
from src.utils.config import load_config


def test_full_demo_exports_repeatability_and_rolling_metrics(config):
    anchor = date(2026, 9, 30)
    manifest = run_pipeline(demo=True, as_of=anchor, root=config.root)
    assert manifest["files"]["personalities.csv"] == 10
    assert manifest["files"]["news_articles.csv"] == 100
    assert manifest["files"]["youtube_videos.csv"] == 40
    assert manifest["files"]["daily_metrics.csv"] == 300
    assert manifest["files"]["personality_brief.csv"] == 10
    assert not config.db_path(False).exists()
    directory = config.export_path(True)
    baseline = {p.name: p.read_bytes() for p in directory.glob("*.csv")}
    for filename, count in manifest["files"].items():
        frame = pd.read_csv(directory / filename)
        assert len(frame) == count
        if "is_demo" in frame:
            assert frame["is_demo"].eq(1).all()
    contents = pd.read_csv(directory / "content.csv")
    mentions = pd.read_csv(directory / "content_personalities.csv")
    topics = pd.read_csv(directory / "content_topics.csv")
    assert contents["content_key"].is_unique
    assert set(mentions["content_key"]) <= set(contents["content_key"])
    assert set(topics["content_key"]) <= set(contents["content_key"])
    brief = pd.read_csv(directory / "personality_brief.csv")
    assert all(len(json.loads(cell)) <= 5 for cell in brief["latest_articles"])
    assert all(len(json.loads(cell)) <= 5 for cell in brief["latest_videos"])
    news = pd.read_csv(directory / "news_articles.csv")
    assert news["title"].str.startswith("[DEMO / FICTIF]").all()
    assert news["url"].str.startswith("https://example.invalid/demo/").all()
    daily = pd.read_csv(directory / "daily_metrics.csv")
    assert daily["visibility_score"].between(0, 100).all()
    assert daily["ccr_relevance_score"].between(0, 100).all()
    assert set(daily["trend"]) <= {"UP", "STABLE", "DOWN"}
    series = daily[daily["personality_id"] == "gabriel_attal"].sort_values("date")
    assert series.iloc[-1]["visibility_avg_7d"] == round(series.tail(7)["visibility_score"].mean(), 2)
    assert series.iloc[-1]["visibility_avg_30d"] == round(series["visibility_score"].mean(), 2)
    assert series.iloc[-1]["visibility_change_7d"] == round(series.iloc[-1]["visibility_score"] - series.iloc[-8]["visibility_score"], 2)
    run_pipeline(demo=True, as_of=anchor, root=config.root)
    assert {p.name: p.read_bytes() for p in directory.glob("*.csv")} == baseline
    with Repository(config.db_path(True), config, True) as repo:
        assert len(repo.connection.execute("SELECT * FROM vw_personality_dashboard").fetchall()) == 300
        assert repo.connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_demo_dates_refresh_without_adding_duplicates(config):
    run_pipeline(True, date(2026, 9, 30), config.root)
    before = pd.read_csv(config.export_path(True) / "news_articles.csv")["published_at"].sort_values().tolist()
    manifest = run_pipeline(True, date(2026, 10, 1), config.root)
    after = pd.read_csv(config.export_path(True) / "news_articles.csv")["published_at"].sort_values().tolist()
    assert manifest["files"]["news_articles.csv"] == 100
    assert manifest["files"]["youtube_videos.csv"] == 40
    assert all(date.fromisoformat(a[:10]) - date.fromisoformat(b[:10]) == timedelta(days=1) for a, b in zip(after, before))


def test_json_only_personality_addition(config):
    path = config.root / "config" / "personalities.json"
    people = json.loads(path.read_text(encoding="utf-8"))
    people.append({"id": "personne_test", "name": "Personne Démo", "status": "suivi", "keywords": ["Personne Démo"]})
    path.write_text(json.dumps(people), encoding="utf-8")
    manifest = run_pipeline(True, date(2026, 9, 30), config.root)
    assert manifest["files"]["personalities.csv"] == 11
    assert manifest["files"]["personality_brief.csv"] == 11
    metrics = pd.read_csv(config.export_path(True) / "daily_metrics.csv")
    assert metrics[metrics["personality_id"] == "personne_test"]["news_count"].sum() > 0


def test_empty_live_pipeline_produces_headers_and_reports_missing_keys(config, monkeypatch):
    monkeypatch.delenv("NEWS_API_KEY", raising=False)
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    path = config.root / "config" / "settings.json"
    settings = json.loads(path.read_text())
    settings["rss_feeds"] = []
    path.write_text(json.dumps(settings))
    manifest = run_pipeline(False, date(2026, 9, 30), config.root)
    assert manifest["files"]["news_articles.csv"] == 0
    assert manifest["files"]["youtube_videos.csv"] == 0
    assert manifest["files"]["daily_metrics.csv"] == 300
    assert {s["status"] for s in manifest["sources"]} == {"skipped_missing_key", "not_configured"}
    assert not config.db_path(True).exists()
    assert pd.read_csv(config.export_path() / "content.csv").empty
