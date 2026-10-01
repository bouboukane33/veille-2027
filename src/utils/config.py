"""Configuration centralisée, indépendante du répertoire de lancement."""
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Config:
    personalities: list[dict]
    topics: dict[str, list[str]]
    settings: dict
    root: Path = ROOT

    @property
    def followed(self) -> list[dict]:
        return [p for p in self.personalities if p["status"] == "suivi"]

    def db_path(self, demo: bool = False) -> Path:
        return self.root / "database" / ("ccr_veille_demo.db" if demo else "ccr_veille.db")

    def export_path(self, demo: bool = False) -> Path:
        return self.root / "data" / "exports" / ("demo" if demo else "live")


def load_config(root: Path = ROOT) -> Config:
    def read(name):
        with (root / "config" / name).open(encoding="utf-8") as stream:
            return json.load(stream)

    personalities, topics, settings = map(read, ["personalities.json", "topics.json", "settings.json"])
    if not isinstance(personalities, list) or not personalities:
        raise ValueError("personalities.json doit être une liste non vide.")
    ids = set()
    for p in personalities:
        if not isinstance(p, dict) or not all(k in p for k in ("id", "name", "status", "keywords")):
            raise ValueError("Chaque personnalité nécessite id, name, status et keywords.")
        if not isinstance(p["id"], str) or not re.fullmatch(r"[a-z0-9_]+", p["id"]) or p["id"] in ids:
            raise ValueError("Identifiants de personnalités invalides ou dupliqués.")
        if not isinstance(p["name"], str) or not p["name"].strip() or p["status"] not in ("suivi", "inactif"):
            raise ValueError("Nom vide ou statut différent de suivi/inactif.")
        if not isinstance(p["keywords"], list) or not p["keywords"] or not all(isinstance(k, str) and k.strip() for k in p["keywords"]):
            raise ValueError("keywords doit être une liste non vide de chaînes.")
        ids.add(p["id"])
    if not isinstance(topics, dict) or not topics or not all(
        re.fullmatch(r"[a-z0-9_]+", key) and isinstance(value, list) and value
        and all(isinstance(k, str) and k.strip() for k in value)
        for key, value in topics.items()
    ):
        raise ValueError("topics.json doit associer des identifiants à des listes de mots-clés.")
    if not isinstance(settings, dict):
        raise ValueError("settings.json doit être un objet.")
    defaults = {
        "lookback_days": 30, "max_news_per_personality": 30,
        "max_youtube_videos_per_personality": 10, "enable_news": True, "enable_youtube": True,
        "rss_feeds": [], "request_timeout_seconds": 15, "request_retries": 1,
        "youtube_max_search_requests": 10, "dedup_title_threshold": 0.94,
        "dedup_date_window_days": 2, "trend_threshold_points": 2.0,
        "visibility_weights": {"news": .35, "views": .30, "engagement": .15, "frequency": .20},
        "relevance_weights": {"volume": .5, "diversity": .3, "recency": .2},
        "relevance_volume_target": 10, "relevance_half_life_days": 7,
        "brief_days": 7, "latest_activity_limit": 200,
    }
    settings = defaults | settings
    for key in ("lookback_days", "max_news_per_personality", "max_youtube_videos_per_personality",
                "request_timeout_seconds", "relevance_volume_target", "relevance_half_life_days",
                "brief_days", "latest_activity_limit"):
        if type(settings[key]) is not int or settings[key] <= 0:
            raise ValueError(f"{key} doit être un entier strictement positif.")
    for key in ("request_retries", "youtube_max_search_requests", "dedup_date_window_days"):
        if type(settings[key]) is not int or settings[key] < 0:
            raise ValueError(f"{key} doit être un entier positif ou nul.")
    if settings["max_youtube_videos_per_personality"] > 50 or settings["max_news_per_personality"] > 100:
        raise ValueError("Limites API : au plus 50 vidéos et 100 articles par personnalité.")
    for key in ("enable_news", "enable_youtube"):
        if type(settings[key]) is not bool:
            raise ValueError(f"{key} doit être un booléen.")
    if not isinstance(settings["rss_feeds"], list) or not all(isinstance(u, str) and u.startswith("https://") for u in settings["rss_feeds"]):
        raise ValueError("rss_feeds doit contenir des URL HTTPS.")
    for key in ("visibility_weights", "relevance_weights"):
        weights = settings[key]
        if not isinstance(weights, dict) or set(weights) != set(defaults[key]):
            raise ValueError(f"Composantes invalides pour {key}.")
        if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 or v > 1 for v in weights.values()) or abs(sum(weights.values()) - 1) > 1e-9:
            raise ValueError(f"Les poids de {key} doivent être positifs et totaliser 1.")
    if not .5 <= settings["dedup_title_threshold"] <= 1 or not 0 <= settings["trend_threshold_points"] <= 100:
        raise ValueError("Seuils de déduplication ou de tendance invalides.")
    return Config(personalities, topics, settings, root)
