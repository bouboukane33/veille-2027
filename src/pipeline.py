"""Orchestration simple et réutilisable par CLI, Dataiku ou ordonnanceur."""
import json
import logging
import os
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from src.collectors.common import CollectionResult, HttpClient
from src.collectors.news_collector import collect_news
from src.collectors.rss_collector import collect_rss
from src.collectors.youtube_collector import collect_youtube
from src.database.models import Content
from src.database.repository import Repository
from src.exports.powerbi_export import export_powerbi
from src.processing.cleaner import clean_content
from src.processing.metrics import build_daily_metrics
from src.processing.topic_classifier import KeywordTopicClassifier
from src.utils.config import ROOT, Config, load_config
from src.utils.demo import generate_demo

logger = logging.getLogger(__name__)


def collect(config: Config, demo: bool, as_of: date) -> tuple[list[Content], list[dict]]:
    if demo:
        contents = generate_demo(config, as_of)
        return contents, [CollectionResult("DEMO / FICTIF", "ok", contents).summary()]
    load_dotenv(config.root / ".env", override=False)
    with HttpClient(config.settings) as client:
        logger.info("[2/8] Collecte presse (NewsAPI et RSS)")
        results = [collect_news(config, client, os.getenv("NEWS_API_KEY"), as_of), collect_rss(config, client, as_of)]
        logger.info("[3/8] Collecte YouTube (métadonnées publiques uniquement)")
        results.append(collect_youtube(config, client, os.getenv("YOUTUBE_API_KEY"), as_of))
    return [c for result in results for c in result.contents], [r.summary() for r in results]


def save_raw(config: Config, demo: bool, contents: list[Content], summaries: list[dict], as_of: date) -> Path:
    path = config.root / "data" / "raw" / ("demo_latest.json" if demo else "live_latest.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"dataset_kind": "demo" if demo else "live", "as_of": as_of.isoformat(),
                               "sources": summaries, "contents": [c.to_dict() for c in contents]},
                              ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_raw(config: Config, demo: bool) -> tuple[list[Content], list[dict], date]:
    path = config.root / "data" / "raw" / ("demo_latest.json" if demo else "live_latest.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["dataset_kind"] != ("demo" if demo else "live"):
        raise ValueError("Le lot brut ne correspond pas au mode choisi.")
    return [Content(**row) for row in data["contents"]], data["sources"], date.fromisoformat(data["as_of"])


def clean_and_limit(config: Config, contents: list[Content], demo: bool) -> list[Content]:
    cleaned = []
    for content in contents:
        try:
            item = clean_content(content, config.followed)
            if item.personality_ids:
                cleaned.append(item)
        except (ValueError, TypeError, AttributeError, OverflowError):
            logger.warning("Contenu sans métadonnées valides ignoré pendant le nettoyage.")
    if demo:
        return cleaned
    # Plafond du lot par type/personnalité, toutes sources presse confondues.
    # Les doublons d'URL/ID du lot ne consomment pas le plafond ; la base traite les titres proches.
    seen, counts, limited = set(), {}, []
    for c in sorted(cleaned, key=lambda c: c.published_at, reverse=True):
        key = (c.content_type, c.video_id if c.content_type == "youtube" else c.url)
        if key in seen:
            continue
        seen.add(key)
        limit = config.settings["max_news_per_personality" if c.content_type == "news" else "max_youtube_videos_per_personality"]
        if any(counts.get((c.content_type, pid), 0) >= limit for pid in c.personality_ids):
            continue
        limited.append(c)
        for pid in c.personality_ids:
            counts[(c.content_type, pid)] = counts.get((c.content_type, pid), 0) + 1
    return limited


def process(config: Config, demo: bool, as_of: date, contents: list[Content], summaries: list[dict]) -> dict:
    logger.info("[4/8] Nettoyage et déduplication")
    cleaned = clean_and_limit(config, contents, demo)
    with Repository(config.db_path(demo), config, demo) as repository:
        repository.initialize()
        counts = repository.save_contents(cleaned)
        logger.info("Stockage : %s nouveaux contenus ; %s doublons/statistiques actualisées.", counts["inserted"], counts["duplicates"])
        logger.info("[5/8] Classification thématique")
        topics_count = repository.reclassify(KeywordTopicClassifier(config.topics))
        logger.info("%s associations contenu/thème.", topics_count)
        logger.info("[6/8] Calcul des indicateurs et scores")
        metrics = build_daily_metrics(repository, as_of)
        logger.info("[7/8] Sauvegarde SQLite : %s lignes d'indicateurs", len(metrics))
        logger.info("[8/8] Exports Power BI")
        manifest = export_powerbi(repository, as_of, summaries)
    report = {"as_of": as_of.isoformat(), "is_demo": demo, "storage": counts,
              "topics": topics_count, "metric_rows": len(metrics), "sources": summaries}
    processed = config.root / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    (processed / ("demo_report.json" if demo else "live_report.json")).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info("Pipeline terminé. Base : %s ; exports : %s", config.db_path(demo), config.export_path(demo))
    if not demo:
        incomplete = [s for s in summaries if s["status"] not in ("ok", "disabled")]
        if incomplete:
            logger.warning("Couverture incomplète : consultez collection_status.csv et les logs.")
        if not cleaned:
            logger.warning("Aucun nouveau contenu collecté ; les exports reflètent uniquement la base existante.")
    return manifest


def run_pipeline(demo: bool = False, as_of: date | None = None, root: Path = ROOT) -> dict:
    as_of = as_of or datetime.now(timezone.utc).date()
    logger.info("=== CCR Veille 2027%s ===", " — DEMO / FICTIF" if demo else "")
    logger.info("[1/8] Chargement configuration et initialisation")
    config = load_config(root)
    # Détecter une erreur de stockage avant de consommer le quota des API.
    with Repository(config.db_path(demo), config, demo) as repository:
        repository.initialize()
    if demo:
        logger.info("[2/8] Génération des articles DEMO / FICTIFS")
        logger.info("[3/8] Génération des vidéos DEMO / FICTIVES")
    contents, summaries = collect(config, demo, as_of)
    save_raw(config, demo, contents, summaries, as_of)
    return process(config, demo, as_of, contents, summaries)
