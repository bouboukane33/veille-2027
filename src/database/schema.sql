PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS personalities (
    personality_id TEXT PRIMARY KEY, name TEXT NOT NULL, status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS news_articles (
    article_id TEXT PRIMARY KEY,
    personality_id TEXT NOT NULL REFERENCES personalities(personality_id),
    title TEXT NOT NULL, description TEXT NOT NULL, source TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE, published_at TEXT NOT NULL, collected_at TEXT NOT NULL,
    keywords TEXT NOT NULL, is_demo INTEGER NOT NULL CHECK (is_demo IN (0, 1))
);
CREATE TABLE IF NOT EXISTS youtube_videos (
    video_id TEXT PRIMARY KEY,
    personality_id TEXT NOT NULL REFERENCES personalities(personality_id),
    title TEXT NOT NULL, channel_name TEXT NOT NULL, description TEXT NOT NULL,
    published_at TEXT NOT NULL, view_count INTEGER, like_count INTEGER, comment_count INTEGER,
    url TEXT NOT NULL UNIQUE, collected_at TEXT NOT NULL,
    keywords TEXT NOT NULL, is_demo INTEGER NOT NULL CHECK (is_demo IN (0, 1))
);
-- Un contenu peut mentionner plusieurs personnalités, sans dupliquer l'article/la vidéo.
CREATE TABLE IF NOT EXISTS content_personalities (
    content_type TEXT NOT NULL CHECK (content_type IN ('news', 'youtube')),
    content_id TEXT NOT NULL, personality_id TEXT NOT NULL REFERENCES personalities(personality_id),
    matched_keywords TEXT NOT NULL,
    PRIMARY KEY (content_type, content_id, personality_id)
);
CREATE TABLE IF NOT EXISTS content_topics (
    content_type TEXT NOT NULL CHECK (content_type IN ('news', 'youtube')),
    content_id TEXT NOT NULL, topic TEXT NOT NULL, score REAL NOT NULL,
    matched_keywords TEXT NOT NULL,
    PRIMARY KEY (content_type, content_id, topic)
);
CREATE TABLE IF NOT EXISTS article_url_aliases (
    url TEXT PRIMARY KEY, article_id TEXT NOT NULL REFERENCES news_articles(article_id)
);
CREATE TABLE IF NOT EXISTS daily_metrics (
    date TEXT NOT NULL, personality_id TEXT NOT NULL REFERENCES personalities(personality_id),
    news_count INTEGER NOT NULL, youtube_video_count INTEGER NOT NULL,
    youtube_views INTEGER NOT NULL, youtube_likes INTEGER NOT NULL, youtube_comments INTEGER NOT NULL,
    youtube_stats_known_count INTEGER NOT NULL,
    topic_ccr_count INTEGER NOT NULL, visibility_score REAL NOT NULL, ccr_relevance_score REAL NOT NULL,
    visibility_yesterday REAL, visibility_delta REAL,
    visibility_avg_7d REAL NOT NULL, visibility_avg_30d REAL NOT NULL,
    visibility_7d_ago REAL, visibility_change_7d REAL,
    trend TEXT NOT NULL, is_demo INTEGER NOT NULL CHECK (is_demo IN (0, 1)),
    PRIMARY KEY (date, personality_id)
);
CREATE INDEX IF NOT EXISTS idx_news_published ON news_articles(published_at);
CREATE INDEX IF NOT EXISTS idx_videos_published ON youtube_videos(published_at);
CREATE INDEX IF NOT EXISTS idx_mentions_personality ON content_personalities(personality_id);

CREATE VIEW IF NOT EXISTS vw_all_content AS
SELECT 'news' AS content_type, article_id AS content_id, title, description, source, url,
       published_at, collected_at, is_demo, NULL AS view_count, NULL AS like_count, NULL AS comment_count
FROM news_articles
UNION ALL
SELECT 'youtube', video_id, title, description, channel_name, url,
       published_at, collected_at, is_demo, view_count, like_count, comment_count
FROM youtube_videos;

CREATE VIEW IF NOT EXISTS vw_personality_dashboard AS
SELECT p.personality_id, p.name, d.date, d.news_count, d.youtube_video_count,
       d.youtube_views, d.youtube_likes, d.topic_ccr_count AS ccr_topic_count,
       d.visibility_score, d.ccr_relevance_score, d.trend,
       d.visibility_yesterday, d.visibility_delta, d.visibility_avg_7d, d.visibility_avg_30d,
       d.visibility_7d_ago, d.visibility_change_7d, d.is_demo
FROM personalities p JOIN daily_metrics d USING (personality_id)
WHERE p.status = 'suivi';
