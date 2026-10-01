from _bootstrap import arguments, execute
from src.database.repository import Repository
from src.utils.config import load_config
from src.utils.logging import configure_logging


def main():
    args = arguments("Initialiser SQLite et synchroniser les personnalités")
    configure_logging(args.demo)
    config = load_config()
    with Repository(config.db_path(args.demo), config, args.demo) as repository:
        repository.initialize()
    print(f"Base initialisée : {config.db_path(args.demo)}")


if __name__ == "__main__":
    execute(main)
