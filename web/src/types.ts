export interface Person {
  personality_id: string;
  name: string;
  status: 'suivi' | 'inactif';
  created_at: string;
  is_demo: number;
}
export interface Content {
  content_key: string;
  content_type: 'news' | 'youtube';
  content_id: string;
  title: string;
  description: string;
  source: string;
  url: string;
  published_at: string;
  collected_at: string;
  date: string;
  view_count: number | null;
  like_count: number | null;
  comment_count: number | null;
  is_demo: number;
}
export interface Metric {
  date: string;
  personality_id: string;
  news_count: number;
  youtube_video_count: number;
  youtube_views: number;
  youtube_likes: number;
  youtube_comments: number;
  topic_ccr_count: number;
  visibility_score: number;
  ccr_relevance_score: number;
  visibility_delta: number;
  visibility_change_7d: number;
  visibility_avg_7d: number;
  visibility_avg_30d: number;
  trend: 'UP' | 'DOWN' | 'STABLE';
}
export interface Source {
  source: string;
  status: string;
  content_count: number;
  errors: number;
}
export interface Topic {
  topic: string;
  keywords: string[];
}
export interface Brief {
  personality_id: string;
  name: string;
  date: string;
  visibility_score: number;
  ccr_relevance_score: number;
  visibility_change_7d: number;
  visibility_avg_7d: number;
  news_count_recent: number;
  youtube_video_count_recent: number;
  brief_days: number;
  top_5_topics: string[];
  latest_articles: { title: string; url: string; published_at: string }[];
  latest_videos: { title: string; url: string; published_at: string }[];
  latest_ccr_content_title: string;
  latest_ccr_content_url: string;
  latest_ccr_content_date: string;
  latest_ccr_topics: string[];
}
export interface Dataset {
  schema_version: number;
  mode: 'live' | 'demo';
  as_of: string;
  generated_at: string;
  revision?: number;
  updated_at?: string;
  sources: Source[];
  columns: Record<string, string[]>;
  tables: {
    personalities: Person[];
    content: Content[];
    daily_metrics: Metric[];
    topics: Topic[];
    content_personalities: {
      content_key: string;
      personality_id: string;
      matched_keywords: string[];
    }[];
    content_topics: {
      content_key: string;
      topic: string;
      score: number;
      matched_keywords: string[];
    }[];
    personality_brief: Brief[];
    [key: string]: unknown[];
  };
}
export interface ApiError {
  code: string;
  message: string;
  missing?: string[];
}
