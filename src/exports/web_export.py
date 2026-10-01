"""Contrat JSON du dashboard, construit à partir des exports Power BI vérifiés."""
import csv
import json
from pathlib import Path

from src.utils.config import Config

INTEGER_COLUMNS = {
    "is_demo", "news_count", "youtube_video_count", "youtube_views", "youtube_likes", "youtube_comments",
    "youtube_stats_known_count", "topic_ccr_count", "ccr_topic_count", "view_count", "like_count", "comment_count",
    "is_ccr", "news_count_recent", "youtube_video_count_recent", "brief_days", "followed_personalities",
    "news_articles", "youtube_videos", "ccr_contents", "content_count", "errors",
}
FLOAT_COLUMNS = {
    "score", "visibility_score", "ccr_relevance_score", "visibility_yesterday", "visibility_delta",
    "visibility_avg_7d", "visibility_avg_30d", "visibility_7d_ago", "visibility_change_7d",
}
JSON_COLUMNS = {"keywords", "matched_keywords", "topics", "top_5_topics", "latest_articles", "latest_videos", "latest_ccr_topics"}


def build_web_dataset(config: Config, demo: bool = False) -> dict:
    directory = config.export_path(demo)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest["dataset_kind"] != ("DEMO / FICTIF" if demo else "LIVE"):
        raise ValueError("Mode des exports incompatible.")
    tables, columns = {}, {}
    for filename, expected_count in manifest["files"].items():
        if not filename.endswith(".csv") or Path(filename).name != filename:
            raise ValueError("Nom d'export invalide.")
        with (directory / filename).open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            columns[filename[:-4]] = reader.fieldnames
            rows = []
            for original in reader:
                row = {}
                for key, value in original.items():
                    if key in INTEGER_COLUMNS or key in FLOAT_COLUMNS:
                        row[key] = None if value == "" else (int(float(value)) if key in INTEGER_COLUMNS else float(value))
                    elif key in JSON_COLUMNS:
                        row[key] = json.loads(value) if value else []
                    else:
                        row[key] = value
                rows.append(row)
        if len(rows) != expected_count:
            raise ValueError("Exports incohérents : régénérez le pipeline avant publication.")
        tables[filename[:-4]] = rows
    return {"schema_version": 1, "mode": "demo" if demo else "live", "as_of": manifest["as_of"],
            "generated_at": manifest["generated_at"], "sources": manifest["sources"],
            "tables": tables, "columns": columns}


def write_web_dataset(config: Config, path: Path, demo: bool = False) -> dict:
    dataset = build_web_dataset(config, demo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dataset, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return dataset
