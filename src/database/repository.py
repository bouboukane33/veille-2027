"""Accès SQLite et transactions regroupés pour faciliter une migration future."""
import hashlib
import json
import sqlite3
from pathlib import Path

from src.database.models import Content
from src.processing.cleaner import detect_personalities, utc_now
from src.processing.deduplicator import similar_article
from src.processing.topic_classifier import TopicClassifier
from src.utils.config import Config


class Repository:
    def __init__(self, path: Path, config: Config, demo: bool = False):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, timeout=30)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.config, self.demo = config, demo

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        if exc_type:
            self.connection.rollback()
        self.connection.close()

    def initialize(self) -> None:
        self.connection.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
        kind = "demo" if self.demo else "live"
        existing = self.connection.execute("SELECT value FROM metadata WHERE key='dataset_kind'").fetchone()
        if existing and existing[0] != kind:
            raise ValueError("Mélange démo/réel refusé : utilisez des bases séparées.")
        with self.connection:
            self.connection.execute("INSERT OR IGNORE INTO metadata VALUES ('dataset_kind', ?)", (kind,))
            self.connection.execute("INSERT OR IGNORE INTO metadata VALUES ('schema_version', '1')")
            self.connection.execute("UPDATE personalities SET status='inactif'")
            for p in self.config.personalities:
                self.connection.execute(
                    """INSERT INTO personalities VALUES (?, ?, ?, ?)
                       ON CONFLICT(personality_id) DO UPDATE SET name=excluded.name, status=excluded.status""",
                    (p["id"], p["name"], p["status"], utc_now()))

    def save_contents(self, contents: list[Content]) -> dict[str, int]:
        counts = {"inserted": 0, "duplicates": 0}
        with self.connection:
            for content in contents:
                if not content.personality_ids:
                    continue
                if content.is_demo != self.demo:
                    raise ValueError("Contenu démo/réel incompatible avec la base.")
                content_id, inserted = self._save_one(content)
                counts["inserted" if inserted else "duplicates"] += 1
                for pid in content.personality_ids:
                    self.connection.execute(
                        "INSERT OR IGNORE INTO content_personalities VALUES (?, ?, ?, ?)",
                        (content.content_type, content_id, pid,
                         json.dumps(content.matched_keywords.get(pid, []), ensure_ascii=False)))
        return counts

    def _save_one(self, c: Content) -> tuple[str, bool]:
        keywords = json.dumps(c.matched_keywords, ensure_ascii=False)
        if c.content_type == "youtube":
            existed = self.connection.execute("SELECT 1 FROM youtube_videos WHERE video_id=?", (c.video_id,)).fetchone()
            self.connection.execute(
                """INSERT INTO youtube_videos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(video_id) DO UPDATE SET
                     title=excluded.title, description=excluded.description, channel_name=excluded.channel_name,
                     published_at=excluded.published_at,
                     view_count=COALESCE(excluded.view_count, youtube_videos.view_count),
                     like_count=COALESCE(excluded.like_count, youtube_videos.like_count),
                     comment_count=COALESCE(excluded.comment_count, youtube_videos.comment_count),
                     collected_at=excluded.collected_at, keywords=excluded.keywords""",
                (c.video_id, c.personality_ids[0], c.title, c.source, c.description,
                 c.published_at, c.view_count, c.like_count, c.comment_count, c.url,
                 c.collected_at, keywords, int(c.is_demo)))
            return c.video_id, not bool(existed)
        existing = self.connection.execute(
            """SELECT article_id FROM news_articles WHERE url=?
               UNION SELECT article_id FROM article_url_aliases WHERE url=?""", (c.url, c.url)).fetchone()
        if not existing:
            candidates = self.connection.execute(
                "SELECT article_id, title, published_at FROM news_articles WHERE ABS(julianday(published_at)-julianday(?)) <= ?",
                (c.published_at, self.config.settings["dedup_date_window_days"]))
            existing = next((r for r in candidates if similar_article(
                c.title, c.published_at, r["title"], r["published_at"],
                self.config.settings["dedup_title_threshold"], self.config.settings["dedup_date_window_days"])), None)
        if existing:
            self.connection.execute("INSERT OR IGNORE INTO article_url_aliases VALUES (?, ?)", (c.url, existing[0]))
            if c.is_demo:
                self.connection.execute(
                    "UPDATE news_articles SET title=?, description=?, published_at=?, collected_at=?, keywords=? WHERE article_id=?",
                    (c.title, c.description, c.published_at, c.collected_at, keywords, existing[0]))
            return existing[0], False
        content_id = hashlib.sha256(c.url.encode()).hexdigest()[:24]
        self.connection.execute("INSERT INTO news_articles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (content_id, c.personality_ids[0], c.title, c.description, c.source, c.url,
             c.published_at, c.collected_at, keywords, int(c.is_demo)))
        return content_id, True

    def reclassify(self, classifier: TopicClassifier) -> int:
        count = 0
        with self.connection:
            self.connection.execute("DELETE FROM content_topics")
            # Refaire les associations permet d'ajouter une personnalité ou de modifier ses alias.
            self.connection.execute("DELETE FROM content_personalities")
            for row in self.connection.execute("SELECT * FROM vw_all_content"):
                text = row["title"] + " " + row["description"]
                mentions = detect_personalities(text, self.config.followed)
                for pid, keywords in mentions.items():
                    self.connection.execute("INSERT INTO content_personalities VALUES (?, ?, ?, ?)",
                        (row["content_type"], row["content_id"], pid, json.dumps(keywords, ensure_ascii=False)))
                for topic, keywords in classifier.classify(text).items():
                    # 1 = présence détectée par mots-clés, pas une probabilité ni une prise de position.
                    self.connection.execute("INSERT INTO content_topics VALUES (?, ?, ?, ?, ?)",
                        (row["content_type"], row["content_id"], topic, 1.0, json.dumps(keywords, ensure_ascii=False)))
                    count += 1
        return count

    def linked_contents(self) -> list[dict]:
        rows = self.connection.execute(
            """SELECT c.*, cp.personality_id FROM vw_all_content c
               JOIN content_personalities cp USING (content_type, content_id)
               JOIN personalities p USING (personality_id) WHERE p.status='suivi'""")
        topics = {}
        for row in self.connection.execute("SELECT content_type, content_id, topic FROM content_topics"):
            topics.setdefault((row[0], row[1]), set()).add(row[2])
        return [dict(r) | {"topics": topics.get((r["content_type"], r["content_id"]), set())} for r in rows]

    def replace_metrics(self, rows: list[dict]) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM daily_metrics")
            if rows:
                columns = list(rows[0])
                sql = f"INSERT INTO daily_metrics ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})"
                self.connection.executemany(sql, [tuple(row[k] for k in columns) for row in rows])
