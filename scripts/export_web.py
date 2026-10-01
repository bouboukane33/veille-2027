from _bootstrap import arguments, execute
from src.exports.web_export import write_web_dataset
from src.utils.config import load_config
from src.utils.logging import configure_logging


def main():
    args = arguments("Exporter les données du dashboard web, sans publication distante")
    configure_logging(args.demo)
    config = load_config()
    path = config.root / "web" / "public" / "demo.json" if args.demo else config.root / "data" / "processed" / "web_live.json"
    dataset = write_web_dataset(config, path, args.demo)
    print(f"Dataset {dataset['mode']} exporté : {path}")


if __name__ == "__main__":
    execute(main)
