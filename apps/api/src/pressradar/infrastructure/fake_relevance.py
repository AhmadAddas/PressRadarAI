from pressradar.domain.clients import Client
from pressradar.domain.media import MediaItem, MediaSourceType
from pressradar.domain.relevance import RelevanceAnalysis


class FakeRelevanceAnalyzer:
    def analyze(
        self,
        *,
        client: Client,
        media_item: MediaItem,
        matched_topics: tuple[str, ...],
    ) -> RelevanceAnalysis:
        score = min(
            98,
            70
            + len(matched_topics) * 8
            + (5 if media_item.source_type is MediaSourceType.JOURNALIST_REQUEST else 0),
        )
        topics = ", ".join(matched_topics)
        location = f" in {client.location}" if client.location else ""
        return RelevanceAnalysis(
            score=score,
            reason=(
                f"This request matches {client.name} at {client.company}{location} "
                f"through their known expertise and monitoring topics: {topics}."
            ),
            matched_topics=matched_topics,
        )
