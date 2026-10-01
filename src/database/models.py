"""Contrat commun aux collecteurs et au stockage ; aucune identité de citoyen."""
from dataclasses import asdict, dataclass, field


@dataclass
class Content:
    content_type: str
    title: str
    description: str
    source: str
    url: str
    published_at: str
    collected_at: str
    personality_ids: list[str] = field(default_factory=list)
    matched_keywords: dict[str, list[str]] = field(default_factory=dict)
    video_id: str | None = None
    view_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None
    is_demo: bool = False

    def to_dict(self) -> dict:
        return asdict(self)
