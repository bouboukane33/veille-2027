import logging
from .config import ROOT


def configure_logging(demo: bool = False) -> None:
    directory = ROOT / "logs"
    directory.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(
            directory / ("pipeline_demo.log" if demo else "pipeline.log"), encoding="utf-8")],
        force=True,
    )
