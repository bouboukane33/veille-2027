"""CSV UTF-8 et tables de liaison explicites pour un modèle Power BI."""
import json
import os
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.database.repository import Repository
from src.processing.cleaner import utc_now


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def export_powerbi(repository: Repository, as_of: date, collection_status: list[dict] | None = None) -> dict:
    config = repository.config
    directory = config.export_path(repository.demo)
    directory.mkdir(parents=True, exist_ok=True)
    frames = {}
    for table, order in {
        "personalities": "personality_id", "news_articles": "published_at, article_id",
        "youtube_videos": "published_at, video_id", "content_topics": "content_type, content_id, topic",
        "content_personalities": "content_type, content_id, personality_id",
        "daily_metrics": "date, personality_id",
    }.items():
        frames[table] = pd.read_sql_query(f"SELECT * FROM {table} ORDER BY {order}", repository.connection)
    for table in ("content_topics", "content_personalities"):
        frames[table].insert(0, "content_key", frames[table]["content_type"] + ":" + frames[table]["content_id"])
    frames["personalities"]["is_demo"] = int(repository.demo)
    for table in ("content_topics", "content_personalities"):
        frames[table]["is_demo"] = int(repository.demo)
    content = pd.read_sql_query("SELECT * FROM vw_all_content ORDER BY published_at, content_type, content_id", repository.connection)
    content.insert(0, "content_key", content["content_type"] + ":" + content["content_id"])
    content["date"] = content["published_at"].str[:10]
    frames["content"] = content
    frames["topics"] = pd.DataFrame([{"topic": t, "keywords": _json(k)} for t, k in config.topics.items()])
    frames["personality_dashboard"] = pd.read_sql_query(
        "SELECT * FROM vw_personality_dashboard ORDER BY date, personality_id", repository.connection)
    linked = repository.linked_contents()
    cutoff = (as_of - timedelta(days=config.settings["lookback_days"] - 1)).isoformat()
    recent = [c for c in linked if cutoff <= c["published_at"][:10] <= as_of.isoformat()]
    recent.sort(key=lambda c: (c["published_at"], c["content_id"], c["personality_id"]), reverse=True)
    activity_columns = ["content_key", "content_type", "content_id", "personality_id", "name", "published_at",
                        "date", "title", "source", "topics", "url", "is_ccr", "is_demo"]
    names = {p["id"]: p["name"] for p in config.followed}
    frames["latest_activity"] = pd.DataFrame([{
        "content_key": c["content_type"] + ":" + c["content_id"],
        "content_type": c["content_type"], "content_id": c["content_id"],
        "personality_id": c["personality_id"], "name": names[c["personality_id"]],
        "published_at": c["published_at"], "date": c["published_at"][:10], "title": c["title"],
        "source": c["source"], "topics": _json(sorted(c["topics"])), "url": c["url"],
        "is_ccr": int(bool(c["topics"])), "is_demo": c["is_demo"],
    } for c in recent[:config.settings["latest_activity_limit"]]], columns=activity_columns)
    metrics = {r["personality_id"]: dict(r) for r in repository.connection.execute(
        "SELECT * FROM daily_metrics WHERE date=?", (as_of.isoformat(),))}
    brief_rows = []
    for p in config.followed:
        metric = metrics.get(p["id"], {})
        personal_recent = [c for c in recent if c["personality_id"] == p["id"] and
                           (as_of - date.fromisoformat(c["published_at"][:10])).days < config.settings["brief_days"]]
        articles = [c for c in personal_recent if c["content_type"] == "news"]
        videos = [c for c in personal_recent if c["content_type"] == "youtube"]
        topic_counts = Counter(t for c in personal_recent for t in c["topics"])
        topic_ranking = sorted(topic_counts, key=lambda t: (-topic_counts[t], t))[:5]
        last_ccr = next((c for c in recent if c["personality_id"] == p["id"] and c["topics"]), None)

        def links(contents):
            return _json([{"title": c["title"], "url": c["url"], "published_at": c["published_at"]} for c in contents[:5]])

        brief_rows.append({
            "personality_id": p["id"], "name": p["name"], "date": as_of.isoformat(),
            "visibility_score": metric.get("visibility_score", 0), "ccr_relevance_score": metric.get("ccr_relevance_score", 0),
            "visibility_change_7d": metric.get("visibility_change_7d"),
            "visibility_avg_7d": metric.get("visibility_avg_7d", 0),
            "news_count_recent": len(articles), "youtube_video_count_recent": len(videos),
            "brief_days": config.settings["brief_days"], "top_5_topics": _json(topic_ranking),
            "latest_articles": links(articles), "latest_videos": links(videos),
            "latest_ccr_content_title": last_ccr["title"] if last_ccr else "",
            "latest_ccr_content_url": last_ccr["url"] if last_ccr else "",
            "latest_ccr_content_date": last_ccr["published_at"] if last_ccr else "",
            "latest_ccr_content_type": last_ccr["content_type"] if last_ccr else "",
            "latest_ccr_topics": _json(sorted(last_ccr["topics"])) if last_ccr else "[]",
            "is_demo": int(repository.demo),
        })
    brief_columns = ["personality_id", "name", "date", "visibility_score", "ccr_relevance_score", "visibility_change_7d",
                     "visibility_avg_7d", "news_count_recent", "youtube_video_count_recent", "brief_days", "top_5_topics",
                     "latest_articles", "latest_videos", "latest_ccr_content_title", "latest_ccr_content_url",
                     "latest_ccr_content_date", "latest_ccr_content_type", "latest_ccr_topics", "is_demo"]
    frames["personality_brief"] = pd.DataFrame(brief_rows, columns=brief_columns)
    topic_content_keys = set(frames["content_topics"]["content_key"])
    today_dashboard = frames["personality_dashboard"]
    today_dashboard = today_dashboard[today_dashboard["date"] == as_of.isoformat()]
    leaders = today_dashboard.sort_values(["visibility_score", "personality_id"], ascending=[False, True])
    leader = leaders.iloc[0] if not leaders.empty and leaders.iloc[0]["visibility_score"] > 0 else None
    frames["overview"] = pd.DataFrame([{
        "date": as_of.isoformat(), "followed_personalities": len(config.followed),
        "news_articles": len(frames["news_articles"]), "youtube_videos": len(frames["youtube_videos"]),
        "ccr_contents": len(topic_content_keys),
        "most_visible_personality_id": leader["personality_id"] if leader is not None else "",
        "most_visible_name": leader["name"] if leader is not None else "",
        "is_demo": int(repository.demo),
    }])
    frames["collection_status"] = pd.DataFrame(collection_status or [], columns=["source", "status", "content_count", "errors"])
    manifest = {
        "dataset_kind": "DEMO / FICTIF" if repository.demo else "LIVE",
        "generated_at": utc_now(), "as_of": as_of.isoformat(),
        "encoding": "UTF-8", "separator": ",", "timezone": "UTC",
        "files": {name + ".csv": len(frame) for name, frame in frames.items()},
        "sources": collection_status or [],
        "note": "Mentions dans titres/descriptions ; aucune attribution de déclaration validée.",
    }
    # Le manifeste est remplacé en dernier ; aucune écriture de CSV partiel n'est publiée.
    with TemporaryDirectory(prefix=".export-", dir=directory) as temp:
        for name, frame in frames.items():
            frame.to_csv(Path(temp) / (name + ".csv"), index=False, encoding="utf-8", sep=",", lineterminator="\n")
        (Path(temp) / "manifest.json").write_text(_json(manifest) + "\n", encoding="utf-8")
        for filename in [*manifest["files"], "manifest.json"]:
            os.replace(Path(temp) / filename, directory / filename)
    return manifest
