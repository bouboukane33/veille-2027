"""Jeu déterministe entièrement fictif, adapté à la liste JSON courante."""
from datetime import date, datetime, timedelta, timezone

from src.database.models import Content
from src.processing.cleaner import iso_datetime
from src.utils.config import Config


def generate_demo(config: Config, as_of: date) -> list[Content]:
    contents = []
    topics = list(config.topics)
    collected = iso_datetime(datetime.combine(as_of, datetime.min.time(), tzinfo=timezone.utc).replace(hour=23))
    for index, p in enumerate(config.followed):
        # Total initial : 100 articles et 40 vidéos ; volumes variables selon la personnalité.
        article_count = 6 + index % 5 * 2
        video_count = 2 + index % 5
        for kind, count in (("news", article_count), ("youtube", video_count)):
            for number in range(count):
                age = (number * 3 + index * 2 + (1 if kind == "youtube" else 0)) % min(30, config.settings["lookback_days"])
                published = iso_datetime(datetime.combine(as_of - timedelta(days=age), datetime.min.time(),
                                                           tzinfo=timezone.utc).replace(hour=8 + number % 10))
                topic = topics[(index + number) % len(topics)]
                keyword = config.topics[topic][0]
                # Quelques contenus hors CCR rendent la pertinence observable.
                subject = keyword if number % 4 else "actualité diplomatique"
                marker = f"{p['id']}/{kind}/{number}"
                # Le titre n'attribue jamais une déclaration fictive à la personne réelle.
                title = f"[DEMO / FICTIF] Dossier {number + 1} mentionnant {p['name']} — {subject}"
                description = ("Contenu de démonstration inventé, sans déclaration réelle. "
                               f"Personnalité mentionnée : {p['name']}. Sujet de test : {subject}.")
                contents.append(Content(
                    content_type=kind, title=title, description=description, source="DEMO — média fictif",
                    url="https://example.invalid/demo/" + marker, published_at=published, collected_at=collected,
                    video_id=f"demo_{p['id']}_{number}" if kind == "youtube" else None,
                    view_count=(index + 1) * (number + 1) * 2300 if kind == "youtube" else None,
                    like_count=(index + 1) * (number + 1) * 65 if kind == "youtube" else None,
                    comment_count=(index + 1) * (number + 1) * 9 if kind == "youtube" else None,
                    is_demo=True,
                ))
    return contents
