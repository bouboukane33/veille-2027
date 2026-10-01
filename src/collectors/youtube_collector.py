import logging
from datetime import date, timedelta

from src.database.models import Content
from src.processing.cleaner import clean_content, utc_now
from src.utils.config import Config
from .common import CollectionResult, HttpClient, SourceError

logger = logging.getLogger(__name__)


def _counter(stats: dict, key: str) -> int | None:
    return max(0, int(stats[key])) if key in stats else None


def collect_youtube(config: Config, client: HttpClient, api_key: str | None, as_of: date) -> CollectionResult:
    if not config.settings["enable_youtube"]:
        return CollectionResult("YouTube", "disabled")
    if not api_key:
        logger.warning("YouTube API non configurée. Collecte YouTube ignorée.")
        return CollectionResult("YouTube", "skipped_missing_key")
    result = CollectionResult("YouTube", "ok")
    since = as_of - timedelta(days=config.settings["lookback_days"] - 1)
    limit = config.settings["youtube_max_search_requests"]
    people = config.followed[:limit]
    if len(people) < len(config.followed):
        logger.warning("YouTube : budget de recherche limité à %s/%s personnalités (ordre JSON).", len(people), len(config.followed))
        result.status = "quota_limited"
    for personality in people:
        try:
            search = client.get_json("https://www.googleapis.com/youtube/v3/search", params={
                "key": api_key, "part": "snippet", "type": "video", "order": "date", "q": personality["name"],
                "publishedAfter": since.isoformat() + "T00:00:00Z",
                "publishedBefore": (as_of + timedelta(days=1)).isoformat() + "T00:00:00Z",
                "maxResults": config.settings["max_youtube_videos_per_personality"], "relevanceLanguage": "fr",
            })
            if "error" in search or not isinstance(search.get("items"), list):
                raise SourceError("YouTube : recherche non exploitable.")
            ids = list(dict.fromkeys(item["id"]["videoId"] for item in search["items"]
                                    if isinstance(item.get("id"), dict) and item["id"].get("videoId")))
            if not ids:
                continue
            # Un appel videos.list récupère les statistiques agrégées, jamais les commentaires.
            details = client.get_json("https://www.googleapis.com/youtube/v3/videos", params={
                "key": api_key, "part": "snippet,statistics", "id": ",".join(ids),
            })
            if "error" in details or not isinstance(details.get("items"), list):
                raise SourceError("YouTube : détails non exploitables.")
            for item in details["items"]:
                try:
                    snippet, stats = item["snippet"], item.get("statistics", {})
                    c = clean_content(Content(
                        content_type="youtube", video_id=item["id"], title=snippet.get("title", ""),
                        description=snippet.get("description", ""), source=snippet.get("channelTitle", ""),
                        url="https://www.youtube.com/watch?v=" + item["id"], published_at=snippet["publishedAt"],
                        collected_at=utc_now(), view_count=_counter(stats, "viewCount"),
                        like_count=_counter(stats, "likeCount"), comment_count=_counter(stats, "commentCount"),
                    ), config.followed)
                    if c.personality_ids and since.isoformat() <= c.published_at[:10] <= as_of.isoformat():
                        result.contents.append(c)
                except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
                    result.errors += 1
                    logger.warning("YouTube : métadonnées de vidéo invalides, vidéo ignorée.")
        except (SourceError, ValueError, KeyError, TypeError, AttributeError) as exc:
            result.errors += 1
            logger.warning("Collecte YouTube pour %s indisponible : %s", personality["id"],
                           str(exc) if isinstance(exc, SourceError) else type(exc).__name__)
            # Éviter de consommer les recherches restantes après une erreur de quota/authentification.
            if isinstance(exc, SourceError) and ("403" in str(exc) or "401" in str(exc)):
                break
    if result.errors:
        result.status = "partial" if result.contents else "failed"
    return result
