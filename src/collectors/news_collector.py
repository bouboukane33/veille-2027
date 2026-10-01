import logging
from datetime import date, timedelta

from src.database.models import Content
from src.processing.cleaner import clean_content, utc_now
from src.utils.config import Config
from .common import CollectionResult, HttpClient, SourceError

logger = logging.getLogger(__name__)


def collect_news(config: Config, client: HttpClient, api_key: str | None, as_of: date) -> CollectionResult:
    if not config.settings["enable_news"]:
        return CollectionResult("NewsAPI", "disabled")
    if not api_key:
        logger.warning("NewsAPI non configurée. Collecte API presse ignorée ; les RSS restent disponibles.")
        return CollectionResult("NewsAPI", "skipped_missing_key")
    result = CollectionResult("NewsAPI", "ok")
    since = as_of - timedelta(days=config.settings["lookback_days"] - 1)
    for personality in config.followed:
        try:
            data = client.get_json("https://newsapi.org/v2/everything", headers={"X-Api-Key": api_key}, params={
                "q": '"' + personality["name"].replace('"', '') + '"', "language": "fr",
                "from": since.isoformat(), "to": as_of.isoformat() + "T23:59:59Z",
                "sortBy": "publishedAt", "pageSize": config.settings["max_news_per_personality"],
            })
            if data.get("status") != "ok" or not isinstance(data.get("articles"), list):
                raise SourceError("NewsAPI : réponse non exploitable (vérifiez le plan et la clé).")
            for item in data["articles"][:config.settings["max_news_per_personality"]]:
                try:
                    c = clean_content(Content(
                        content_type="news", title=item.get("title") or "", description=item.get("description") or "",
                        source=(item.get("source") or {}).get("name") or "NewsAPI",
                        url=item.get("url") or "", published_at=item.get("publishedAt") or "", collected_at=utc_now(),
                    ), config.followed)
                    if c.personality_ids and since.isoformat() <= c.published_at[:10] <= as_of.isoformat():
                        result.contents.append(c)
                except (ValueError, TypeError, AttributeError, OverflowError):
                    logger.warning("NewsAPI : métadonnées d'article invalides, article ignoré.")
                    result.errors += 1
        except (SourceError, ValueError, TypeError, AttributeError) as exc:
            logger.warning("Collecte NewsAPI pour %s indisponible : %s", personality["id"],
                           str(exc) if isinstance(exc, SourceError) else type(exc).__name__)
            result.errors += 1
    if result.errors:
        result.status = "partial" if result.contents else "failed"
    return result
