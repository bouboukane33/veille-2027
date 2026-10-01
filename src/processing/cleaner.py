"""Nettoyage limité aux métadonnées fournies par API/RSS."""
import html
import re
import unicodedata
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.database.models import Content


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def clean_text(value: str | None) -> str:
    parser = _TextParser()
    parser.feed(html.unescape(value or ""))
    return " ".join(" ".join(parser.parts).split())


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def contains_phrase(normalized: str, keyword: str) -> bool:
    phrase = normalize_text(keyword)
    return bool(phrase) and f" {phrase} " in f" {normalized} "


def detect_personalities(text: str, personalities: list[dict]) -> dict[str, list[str]]:
    normalized = normalize_text(text)
    return {p["id"]: matches for p in personalities
            if (matches := [k for k in p["keywords"] if contains_phrase(normalized, k)])}


def iso_datetime(value: str | datetime) -> str:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            value = parsedate_to_datetime(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_now() -> str:
    return iso_datetime(datetime.now(timezone.utc))


def canonical_url(value: str) -> str:
    parts = urlsplit(value.strip())
    if parts.scheme.lower() not in ("https", "http") or not parts.hostname or parts.username or parts.password:
        raise ValueError("URL HTTP(S) publique requise, sans identifiants.")
    # Retirer seulement des paramètres de suivi connus ; préserver les identifiants d'article.
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in ("fbclid", "gclid", "mc_cid", "mc_eid")]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", urlencode(sorted(query)), ""))


def clean_content(content: Content, personalities: list[dict]) -> Content:
    content.title = clean_text(content.title)
    content.description = clean_text(content.description)
    content.source = clean_text(content.source)
    if not content.title or content.content_type not in ("news", "youtube"):
        raise ValueError("Titre ou type de contenu invalide.")
    content.url = canonical_url(content.url)
    content.published_at = iso_datetime(content.published_at)
    content.collected_at = iso_datetime(content.collected_at)
    content.matched_keywords = detect_personalities(content.title + " " + content.description, personalities)
    content.personality_ids = list(content.matched_keywords)
    for key in ("view_count", "like_count", "comment_count"):
        value = getattr(content, key)
        if value is not None:
            setattr(content, key, max(0, int(value)))
    if content.content_type == "youtube" and not content.video_id:
        raise ValueError("video_id requis.")
    return content
