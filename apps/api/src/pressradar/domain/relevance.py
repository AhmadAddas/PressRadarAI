from dataclasses import dataclass


@dataclass(frozen=True)
class RelevanceAnalysis:
    score: int
    reason: str
    matched_topics: tuple[str, ...]

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 100:
            raise ValueError("Relevance score must be between 0 and 100")
        if not self.reason.strip() or len(self.reason) > 2_000:
            raise ValueError("Relevance reason must contain 1 to 2,000 characters")
        if not self.matched_topics or len(self.matched_topics) > 50:
            raise ValueError("Relevance analysis must contain matched topics")
        if any(not topic.strip() or len(topic) > 100 for topic in self.matched_topics):
            raise ValueError("Relevance matched topics are invalid")
