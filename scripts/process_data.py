from _bootstrap import arguments, execute
from src.pipeline import load_raw, process
from src.utils.config import load_config
from src.utils.logging import configure_logging


def main():
    args = arguments("Traiter le dernier lot brut, calculer les scores et exporter")
    configure_logging(args.demo)
    config = load_config()
    contents, summaries, as_of = load_raw(config, args.demo)
    process(config, args.demo, as_of, contents, summaries)


if __name__ == "__main__":
    execute(main)
