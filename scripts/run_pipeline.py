from _bootstrap import arguments, execute
from src.pipeline import run_pipeline
from src.utils.logging import configure_logging


def main():
    args = arguments("Pipeline complet CCR Veille 2027", dated=True)
    configure_logging(args.demo)
    run_pipeline(demo=args.demo, as_of=args.as_of)


if __name__ == "__main__":
    execute(main)
