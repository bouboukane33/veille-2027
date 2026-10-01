import shutil
from pathlib import Path

import pytest

from src.utils.config import ROOT, load_config


@pytest.fixture
def config(tmp_path):
    shutil.copytree(ROOT / "config", tmp_path / "config")
    return load_config(tmp_path)
