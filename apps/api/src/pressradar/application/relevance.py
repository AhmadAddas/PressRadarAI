from typing import Protocol

from pressradar.domain.clients import Client
from pressradar.domain.media import MediaItem
from pressradar.domain.relevance import RelevanceAnalysis


class RelevanceAnalysisError(Exception):
    """Raised when a relevance provider cannot produce a valid analysis."""


class RelevanceAnalyzer(Protocol):
    def analyze(
        self,
        *,
        client: Client,
        media_item: MediaItem,
        matched_topics: tuple[str, ...],
    ) -> RelevanceAnalysis: ...
