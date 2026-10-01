from _bootstrap import arguments, execute
from src.database.repository import Repository
from src.exports.powerbi_export import export_powerbi
from src.utils.config import load_config
from src.utils.logging import configure_logging
from datetime import date
import json


def main():
    args = arguments("Réexporter la base SQLite sans collecte")
    configure_logging(args.demo)
    config = load_config()
    if not config.db_path(args.demo).exists():
        raise FileNotFoundError("Lancez d'abord run_pipeline.py.")
    with Repository(config.db_path(args.demo), config, args.demo) as repository:
        last = repository.connection.execute("SELECT MAX(date) FROM daily_metrics").fetchone()[0]
        if not last:
            raise ValueError("Aucun indicateur : lancez run_pipeline.py ou process_data.py.")
        report_path = config.root / "data" / "processed" / ("demo_report.json" if args.demo else "live_report.json")
        summaries = json.loads(report_path.read_text(encoding="utf-8"))["sources"] if report_path.exists() else []
        manifest = export_powerbi(repository, date.fromisoformat(last), summaries)
    print(f"{len(manifest['files'])} CSV exportés dans {config.export_path(args.demo)}")


if __name__ == "__main__":
    execute(main)
