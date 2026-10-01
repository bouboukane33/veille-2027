from datetime import datetime
from difflib import SequenceMatcher
import re

from .cleaner import normalize_text


def similar_article(title: str, date: str, other_title: str, other_date: str,
                    threshold: float = .94, window_days: int = 2) -> bool:
    """Déduplication conservatrice ; les titres courts restent distincts."""
    a, b = normalize_text(title), normalize_text(other_title)
    if not a or not b:
        return False
    days = abs((datetime.fromisoformat(date.replace("Z", "+00:00")) -
                datetime.fromisoformat(other_date.replace("Z", "+00:00"))).total_seconds()) / 86400
    if days > window_days:
        return False
    if a == b:
        return True
    # Deux titres proches contenant des dates, budgets ou numéros différents peuvent être distincts.
    if re.findall(r"\b\d+\b", a) != re.findall(r"\b\d+\b", b):
        return False
    return len(a) >= 35 and len(b) >= 35 and SequenceMatcher(None, a, b).ratio() >= threshold
