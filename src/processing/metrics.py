from collections import defaultdict
from datetime import date, timedelta

from src.database.repository import Repository
from .scoring import calculate_ccr_relevance_score, calculate_visibility_score, trend_from_delta


def build_daily_metrics(repository: Repository, as_of: date) -> list[dict]:
    """Volumes par jour de publication ; pertinence sur une fenêtre glissante."""
    config = repository.config
    settings = config.settings
    history = max(30, settings["lookback_days"])
    # 30 jours additionnels pour calculer des moyennes complètes dès le premier jour exporté.
    start = as_of - timedelta(days=history + 29)
    by_person = defaultdict(list)
    for c in repository.linked_contents():
        c["day"] = date.fromisoformat(c["published_at"][:10])
        if c["day"] <= as_of:
            by_person[c["personality_id"]].append(c)
    all_rows, score_history = [], defaultdict(list)
    for offset in range((as_of - start).days + 1):
        day = start + timedelta(days=offset)
        daily_rows = []
        for personality in config.followed:
            pid = personality["id"]
            contents = by_person[pid]
            daily = [c for c in contents if c["day"] == day]
            videos = [c for c in daily if c["content_type"] == "youtube"]
            relevant = [c for c in contents if c["topics"] and
                        0 <= (day - c["day"]).days < settings["lookback_days"]]
            topics = set().union(*(c["topics"] for c in relevant)) if relevant else set()
            row = {
                "date": day.isoformat(), "personality_id": pid,
                "news_count": sum(c["content_type"] == "news" for c in daily),
                "youtube_video_count": len(videos),
                "youtube_views": sum(c["view_count"] or 0 for c in videos),
                "youtube_likes": sum(c["like_count"] or 0 for c in videos),
                "youtube_comments": sum(c["comment_count"] or 0 for c in videos),
                "youtube_stats_known_count": sum(c["view_count"] is not None for c in videos),
                "topic_ccr_count": sum(bool(c["topics"]) for c in daily),
                "ccr_relevance_score": calculate_ccr_relevance_score(
                    [(day - c["day"]).days for c in relevant], len(topics), len(config.topics),
                    settings["relevance_volume_target"], settings["relevance_half_life_days"],
                    settings["relevance_weights"]),
            }
            daily_rows.append(row)
        maxima = {
            "news": max((r["news_count"] for r in daily_rows), default=0),
            "views": max((r["youtube_views"] for r in daily_rows), default=0),
            "engagement": max((r["youtube_likes"] + r["youtube_comments"] for r in daily_rows), default=0),
            "frequency": max((r["news_count"] + r["youtube_video_count"] for r in daily_rows), default=0),
        }
        for row in daily_rows:
            pid = row["personality_id"]
            score = calculate_visibility_score(row["news_count"], row["youtube_views"],
                row["youtube_likes"] + row["youtube_comments"], row["news_count"] + row["youtube_video_count"],
                maxima, settings["visibility_weights"])
            prev = score_history[pid][-1] if score_history[pid] else None
            week_ago = score_history[pid][-7] if len(score_history[pid]) >= 7 else None
            score_history[pid].append(score)
            delta = round(score - prev, 2) if prev is not None else None
            row.update({
                "visibility_score": score, "visibility_yesterday": prev, "visibility_delta": delta,
                "visibility_avg_7d": round(sum(score_history[pid][-7:]) / len(score_history[pid][-7:]), 2),
                "visibility_avg_30d": round(sum(score_history[pid][-30:]) / len(score_history[pid][-30:]), 2),
                "visibility_7d_ago": week_ago,
                "visibility_change_7d": round(score - week_ago, 2) if week_ago is not None else None,
                "trend": trend_from_delta(delta or 0, settings["trend_threshold_points"]),
                "is_demo": int(repository.demo),
            })
            if day >= as_of - timedelta(days=history - 1):
                all_rows.append(row)
    repository.replace_metrics(all_rows)
    return all_rows
