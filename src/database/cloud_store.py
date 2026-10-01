"""État durable PostgreSQL/Supabase ; le moteur Python existant travaille en SQLite.

Le snapshot inclut l'archive entière, pas seulement les données des graphiques.
Publication atomique et révision attendue protègent contre les écritures concurrentes.
"""
import json
from urllib.parse import urlsplit

import requests

from src.database.repository import Repository

TABLES = ("metadata", "personalities", "news_articles", "youtube_videos", "article_url_aliases",
          "content_personalities", "content_topics", "daily_metrics")


class CloudStoreError(RuntimeError):
    pass


class CloudStore:
    def __init__(self, url: str, key: str):
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError("SUPABASE_URL doit être l'URL HTTPS publique du projet, sans identifiants.")
        if not key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY est requise pour restaurer/publier les données.")
        self.url = url.rstrip("/")
        self.headers = {"apikey": key, "Authorization": "Bearer " + key, "Content-Type": "application/json"}

    def _request(self, method: str, path: str, **kwargs):
        try:
            response = requests.request(method, self.url + "/rest/v1/" + path,
                                        headers=self.headers, timeout=45, allow_redirects=False, **kwargs)
            if response.status_code >= 300:
                raise CloudStoreError(f"Supabase HTTP {response.status_code} : vérifiez le schéma, les accès et la révision.")
            return response.json()
        except requests.RequestException:
            raise CloudStoreError("Supabase inaccessible ; état distant inchangé ou publication à vérifier.") from None
        except ValueError:
            raise CloudStoreError("Réponse Supabase invalide.") from None

    def read(self) -> dict | None:
        payload = self._request("GET", "ccr_snapshots", params={"id": "eq.live", "select": "revision,tables,dataset", "limit": "1"})
        if not isinstance(payload, list) or len(payload) > 1:
            raise CloudStoreError("Snapshot Supabase invalide.")
        return payload[0] if payload else None

    def publish(self, repository: Repository, dataset: dict, expected_revision: int) -> int:
        if repository.demo or dataset.get("mode") != "live":
            raise ValueError("Publication de données fictives dans le stockage réel refusée.")
        tables = {table: [dict(row) for row in repository.connection.execute(f"SELECT * FROM {table}")] for table in TABLES}
        if any(row.get("is_demo", 0) != 0 for rows in tables.values() for row in rows):
            raise ValueError("La base contient des données fictives.")
        # Vercel limite la taille des réponses serverless ; garder une marge pour le JSON HTTP.
        if len(json.dumps(dataset, ensure_ascii=False).encode("utf-8")) > 3_500_000:
            raise ValueError("Dataset web trop volumineux : ajouter une pagination avant publication.")
        result = self._request("POST", "rpc/publish_ccr_snapshot", json={
            "dataset_json": dataset, "tables_json": tables, "expected_revision": expected_revision,
        })
        if type(result) is not int:
            raise CloudStoreError("Révision de publication non confirmée.")
        return result


def restore_snapshot(repository: Repository, snapshot: dict) -> None:
    if repository.demo or snapshot.get("dataset", {}).get("mode") != "live":
        raise ValueError("Restauration réelle uniquement.")
    tables = snapshot.get("tables")
    if not isinstance(tables, dict) or set(tables) != set(TABLES):
        raise ValueError("Schéma du snapshot incompatible.")
    kinds = [r.get("value") for r in tables["metadata"] if r.get("key") == "dataset_kind"]
    if kinds != ["live"] or any(row.get("is_demo", 0) != 0 for rows in tables.values() for row in rows):
        raise ValueError("Snapshot contenant des données fictives refusé.")
    with repository.connection:
        for table in reversed(TABLES):
            repository.connection.execute(f"DELETE FROM {table}")
        for table in TABLES:
            columns = [r[1] for r in repository.connection.execute(f"PRAGMA table_info({table})")]
            sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})"
            for row in tables[table]:
                if set(row) != set(columns):
                    raise ValueError("Colonnes du snapshot incompatibles.")
                repository.connection.execute(sql, tuple(row[key] for key in columns))
