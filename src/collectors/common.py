"""Client HTTP partagé : délais, retries bornés, erreurs sans clés API."""
import logging
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.database.models import Content

logger = logging.getLogger(__name__)


class SourceError(RuntimeError):
    pass


@dataclass
class CollectionResult:
    source: str
    status: str
    contents: list[Content] = field(default_factory=list)
    errors: int = 0

    def summary(self) -> dict:
        return {"source": self.source, "status": self.status,
                "content_count": len(self.contents), "errors": self.errors}


class HttpClient:
    def __init__(self, settings: dict):
        # Les avertissements de retry urllib3 peuvent inclure l'URL et sa clé YouTube.
        # Le client produit lui-même une erreur expurgée après les retries.
        logging.getLogger("urllib3.connectionpool").setLevel(logging.CRITICAL)
        self.timeout = settings["request_timeout_seconds"]
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "CCR-Veille-2027-POC/1.0 (public metadata monitoring)"
        retry = Retry(total=settings["request_retries"], backoff_factor=.5,
                      status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET",),
                      raise_on_status=False, respect_retry_after_header=False)
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.session.close()

    def get(self, url: str, **kwargs):
        host = urlsplit(url).hostname
        try:
            response = self.session.get(url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            status = exc.response.status_code if exc.response is not None else "réseau"
            # Ne pas journaliser str(exc), l'URL préparée, les en-têtes ni le corps de la réponse.
            raise SourceError(f"{host} : erreur {status} ({type(exc).__name__})") from None

    def get_json(self, url: str, **kwargs) -> dict:
        try:
            # Une API ne doit pas rediriger sa clé vers un autre hôte.
            payload = self.get(url, allow_redirects=False, **kwargs).json()
        except ValueError:
            raise SourceError(f"{urlsplit(url).hostname} : réponse JSON invalide") from None
        if not isinstance(payload, dict):
            raise SourceError(f"{urlsplit(url).hostname} : objet JSON attendu")
        return payload
