from datetime import date
from types import SimpleNamespace

import pytest
import requests

from src.collectors.common import HttpClient, SourceError
from src.collectors.news_collector import collect_news
from src.collectors.rss_collector import collect_rss
from src.collectors.youtube_collector import collect_youtube


class FakeClient:
    def __init__(self, payloads=None, xml=None, error=None):
        self.payloads = iter(payloads or [])
        self.xml, self.error, self.calls = xml, error, []

    def get_json(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return next(self.payloads)

    def get(self, url):
        if self.error:
            raise self.error
        return SimpleNamespace(content=self.xml)


def test_news_contract_and_missing_key(config):
    config.personalities[:] = config.personalities[:1]
    client = FakeClient([{"status": "ok", "articles": [{
        "title": "Édouard Philippe — climat", "description": "Assurance", "source": {"name": "Presse test"},
        "url": "https://example.org/a", "publishedAt": "2026-09-30T10:00:00Z"}]}])
    result = collect_news(config, client, "test-key", date(2026, 9, 30))
    assert result.status == "ok"
    assert result.contents[0].personality_ids == ["edouard_philippe"]
    assert client.calls[0][1]["headers"] == {"X-Api-Key": "test-key"}
    assert collect_news(config, FakeClient(), None, date(2026, 9, 30)).status == "skipped_missing_key"


def test_rss_date_filter_and_multimention(config):
    config.settings["rss_feeds"] = ["https://example.org/feed"]
    xml = b'''<?xml version="1.0"?><rss version="2.0"><channel><title>RSS test</title>
    <item><title>Edouard Philippe et Gabriel Attal : climat</title><link>https://example.org/a</link>
    <description>Assurance</description><pubDate>Wed, 30 Sep 2026 10:00:00 GMT</pubDate></item>
    <item><title>Gabriel Attal</title><link>https://example.org/old</link>
    <pubDate>Wed, 01 Jan 2020 10:00:00 GMT</pubDate></item>
    </channel></rss>'''
    result = collect_rss(config, FakeClient(xml=xml), date(2026, 9, 30))
    assert result.status == "ok"
    assert len(result.contents) == 1
    assert set(result.contents[0].personality_ids) == {"edouard_philippe", "gabriel_attal"}


def test_rss_html_response_is_not_a_valid_empty_feed(config):
    config.settings["rss_feeds"] = ["https://example.org/feed"]
    result = collect_rss(config, FakeClient(xml=b"<html><body>Access denied</body></html>"), date(2026, 9, 30))
    assert result.status == "failed"
    assert not result.contents


def test_youtube_batches_statistics_and_limits_searches(config):
    config.settings["youtube_max_search_requests"] = 1
    client = FakeClient([
        {"items": [{"id": {"videoId": "abc"}}]},
        {"items": [{"id": "abc", "snippet": {
            "title": "Édouard Philippe : assurance", "description": "Climat", "channelTitle": "Média public",
            "publishedAt": "2026-09-30T10:00:00Z"}, "statistics": {"viewCount": "120", "commentCount": "2"}}]},
    ])
    result = collect_youtube(config, client, "test-key", date(2026, 9, 30))
    assert result.status == "quota_limited"
    assert len(client.calls) == 2
    assert client.calls[1][1]["params"]["part"] == "snippet,statistics"
    assert result.contents[0].view_count == 120
    assert result.contents[0].like_count is None
    assert result.contents[0].comment_count == 2


def test_source_outage_does_not_raise_or_log_key(config, caplog):
    result = collect_news(config, FakeClient(error=SourceError("newsapi.org : erreur 503")), "secret-test", date(2026, 9, 30))
    assert result.status == "failed"
    assert result.errors == 10
    assert "secret-test" not in caplog.text


def test_http_error_sanitizes_prepared_url(config, monkeypatch):
    with HttpClient(config.settings) as client:
        def fail(*args, **kwargs):
            raise requests.ConnectionError("https://googleapis.com?key=secret-value")
        monkeypatch.setattr(client.session, "get", fail)
        with pytest.raises(SourceError) as error:
            client.get_json("https://www.googleapis.com/youtube/v3/search", params={"key": "secret-value"})
        assert "secret-value" not in str(error.value)
        assert "www.googleapis.com" in str(error.value)
