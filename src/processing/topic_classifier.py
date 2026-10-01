from typing import Protocol

from .cleaner import contains_phrase, normalize_text


class TopicClassifier(Protocol):
    """Point de remplacement pour une future classification sémantique."""
    def classify(self, text: str) -> dict[str, list[str]]: ...


class KeywordTopicClassifier:
    def __init__(self, topics: dict[str, list[str]]):
        self.topics = topics

    def classify(self, text: str) -> dict[str, list[str]]:
        normalized = normalize_text(text)
        return {topic: found for topic, keywords in self.topics.items()
                if (found := [k for k in keywords if contains_phrase(normalized, k)])}
