import json
from datetime import date

import pytest
import requests

from src.database.cloud_store import CloudStore, CloudStoreError, TABLES, restore_snapshot
from src.database.models import Content
from src.database.repository import Repository
from src.exports.web_export import build_web_dataset
from src.pipeline import process, run_pipeline
from src.processing.cleaner import clean_content


def test_web_export_keeps_types_ids_and_demo_labels(config):
    run_pipeline(True, date(2026, 10, 1), config.root)
    dataset = build_web_dataset(config, True)
    assert dataset['mode'] == 'demo'
    assert len(dataset['tables']['content']) == 140
    assert len(dataset['tables']['daily_metrics']) == 300
    assert type(dataset['tables']['daily_metrics'][0]['visibility_score']) is float
    assert isinstance(dataset['tables']['content_topics'][0]['matched_keywords'], list)
    assert isinstance(dataset['tables']['content'][0]['content_id'], str)


def test_cloud_round_trip_preserves_corpus_and_aliases(config, monkeypatch):
    content = clean_content(Content('news', 'Gabriel Attal : prévention et climat', '', 'RSS test',
        'https://example.org/a', '2026-10-01T06:00:00Z', '2026-10-01T07:00:00Z'), config.followed)
    process(config, False, date(2026, 10, 1), [content], [{'source': 'RSS', 'status': 'ok', 'content_count': 1, 'errors': 0}])
    store = CloudStore('https://example.supabase.co', 'test-only-secret')
    captured = {}

    def request(method, url, **kwargs):
        assert kwargs['headers']['apikey'] == 'test-only-secret'
        assert kwargs['allow_redirects'] is False
        captured.update(kwargs['json'])
        return type('Response', (), {'status_code': 200, 'json': lambda self: 1})()

    monkeypatch.setattr(requests, 'request', request)
    dataset = build_web_dataset(config)
    with Repository(config.db_path(), config) as repository:
        assert store.publish(repository, dataset, 0) == 1
        original = {t: [dict(r) for r in repository.connection.execute(f'SELECT * FROM {t}')] for t in TABLES}
        repository.connection.execute('DELETE FROM news_articles')
        repository.connection.commit()
        restore_snapshot(repository, {'tables': captured['tables_json'], 'dataset': captured['dataset_json'], 'revision': 1})
        assert {t: [dict(r) for r in repository.connection.execute(f'SELECT * FROM {t}')] for t in TABLES} == original
    assert 'test-only-secret' not in json.dumps(captured)


def test_demo_cannot_be_published_or_restored_as_live(config):
    run_pipeline(True, date(2026, 10, 1), config.root)
    with Repository(config.db_path(True), config, True) as repo:
        with pytest.raises(ValueError, match='fictives'):
            CloudStore('https://example.supabase.co', 'test').publish(repo, build_web_dataset(config, True), 0)
    with Repository(config.db_path(), config) as repo:
        repo.initialize()
        with pytest.raises(ValueError):
            restore_snapshot(repo, {'dataset': {'mode': 'demo'}, 'tables': {}})


def test_cloud_http_errors_never_expose_keys(monkeypatch):
    def fail(*args, **kwargs):
        raise requests.ConnectionError('private-key-value')
    monkeypatch.setattr(requests, 'request', fail)
    with pytest.raises(CloudStoreError) as error:
        CloudStore('https://example.supabase.co', 'private-key-value').read()
    assert 'private-key-value' not in str(error.value)
