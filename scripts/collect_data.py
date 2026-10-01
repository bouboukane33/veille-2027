from datetime import datetime, timezone

from _bootstrap import arguments, execute
from src.pipeline import collect, save_raw
from src.utils.config import load_config
from src.utils.logging import configure_logging


def main():
    args = arguments("Collecter uniquement les métadonnées brutes", dated=True)
    configure_logging(args.demo)
    config = load_config()
    as_of = args.as_of or datetime.now(timezone.utc).date()
    contents, summaries = collect(config, args.demo, as_of)
    print(f"Lot brut : {save_raw(config, args.demo, contents, summaries, as_of)}")
    for summary in summaries:
        print(summary)


if __name__ == "__main__":
    execute(main)
