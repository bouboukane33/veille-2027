import logging
from datetime import date, timedelta
from urllib.parse import urlsplit

import feedparser

from src.database.models import Content
from src.processing.cleaner import clean_content, utc_now
from src.utils.config import Config
from .common import CollectionResult, HttpClient, SourceError

logger = logging.getLogger(__name__)


def collect_rss(config: Config, client: HttpClient, as_of: date) -> CollectionResult:
    if not config.settings["enable_news"]:
        return CollectionResult("RSS", "disabled")
    result = CollectionResult("RSS", "ok" if config.settings["rss_feeds"] else "not_configured")
    since = as_of - timedelta(days=config.settings["lookback_days"] - 1)
    for url in config.settings["rss_feeds"]:
        try:
            # feedparser ne gère pas lui-même le réseau : requests conserve délais et TLS vérifié.
            feed = feedparser.parse(client.get(url).content)
            if not feed.version or (feed.bozo and not feed.entries):
                raise SourceError(f"{urlsplit(url).hostname} : flux RSS/Atom invalide")
            if feed.bozo:
                logger.warning("RSS %s : flux partiellement mal formé.", urlsplit(url).hostname)
                result.errors += 1
            for item in feed.entries:
                try:
                    c = clean_content(Content(
                        content_type="news", title=item.get("title", ""),
                        description=item.get("summary", ""), source=feed.feed.get("title", urlsplit(url).hostname),
                        url=item.get("link", ""), published_at=item.get("published") or item.get("updated") or "",
                        collected_at=utc_now(),
                    ), config.followed)
                    if c.personality_ids and since.isoformat() <= c.published_at[:10] <= as_of.isoformat():
                        result.contents.append(c)
                except (ValueError, TypeError, AttributeError, OverflowError):
                    # Une date manquante n'est jamais remplacée par une date de collecte inventée.
                    result.errors += 1
                    logger.warning("RSS %s : entrée sans métadonnées valides ignorée.", urlsplit(url).hostname)
        except (SourceError, ValueError, TypeError) as exc:
            result.errors += 1
            logger.warning("Collecte RSS indisponible : %s", str(exc) if isinstance(exc, SourceError) else type(exc).__name__)
    if result.errors:
        result.status = "partial" if result.contents else "failed"
    return result
