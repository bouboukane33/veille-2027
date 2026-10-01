import logging
import os
from dotenv import load_dotenv

from _bootstrap import execute
from src.database.cloud_store import CloudStore, CloudStoreError, restore_snapshot
from src.database.repository import Repository
from src.exports.web_export import build_web_dataset
from src.pipeline import run_pipeline
from src.utils.config import load_config
from src.utils.logging import configure_logging


def cloud_main():
    configure_logging()
    config = load_config()
    load_dotenv(config.root / ".env", override=False)
    store = CloudStore(os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
    snapshot = store.read()  # Ne pas collecter si l'archive distante est inaccessible.
    revision = snapshot["revision"] if snapshot else 0
    with Repository(config.db_path(), config) as repository:
        repository.initialize()
        if snapshot:
            restore_snapshot(repository, snapshot)
    manifest = run_pipeline()
    # Avec un premier corpus vide ET toutes les sources indisponibles, ne pas publier une fausse veille.
    if not snapshot and manifest["files"]["news_articles.csv"] + manifest["files"]["youtube_videos.csv"] == 0:
        raise ValueError("Aucun contenu réel : configurez une source accessible avant la première publication.")
    dataset = build_web_dataset(config)
    with Repository(config.db_path(), config) as repository:
        published_revision = store.publish(repository, dataset, revision)
    logging.info("Publication Supabase confirmée : révision %s.", published_revision)


def main():
    try:
        cloud_main()
    except CloudStoreError as exc:
        raise ValueError(str(exc)) from None


if __name__ == "__main__":
    execute(main)
