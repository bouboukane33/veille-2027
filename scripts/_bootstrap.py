"""Permet `python scripts/...py` depuis n'importe quel répertoire."""
import argparse
import logging
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def arguments(description: str, dated: bool = False):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--demo", action="store_true", help="Utiliser la base et les exports DEMO / FICTIFS isolés.")
    if dated:
        parser.add_argument("--as-of", type=date.fromisoformat, help="Date de référence ISO (défaut : aujourd'hui UTC).")
    return parser.parse_args()


def execute(function):
    try:
        function()
    except (KeyboardInterrupt, SystemExit):
        raise
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        logging.error("Échec local : %s", exc)
        raise SystemExit(1) from None
    except Exception as exc:
        # Erreur fatale locale : code non nul, jamais de représentation d'une requête contenant une clé.
        logging.error("Échec local (%s). Vérifiez configuration, fichiers et permissions.", type(exc).__name__)
        raise SystemExit(1) from None
