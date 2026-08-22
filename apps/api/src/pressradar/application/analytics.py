from typing import Protocol

from pressradar.domain.analytics import AnalyticsSummary, ProductEvent


class AnalyticsError(Exception):
    """Raised when the separate analytics pipeline is unavailable."""


class AnalyticsStore(Protocol):
    def record(self, event: ProductEvent) -> None: ...

    def summary(self, *, workspace_id: str) -> AnalyticsSummary: ...


class AnalyticsService:
    def __init__(self, store: AnalyticsStore) -> None:
        self._store = store

    def track(self, event: ProductEvent) -> None:
        try:
            self._store.record(event)
        except AnalyticsError:
            pass

    def summary(self, *, workspace_id: str) -> AnalyticsSummary:
        return self._store.summary(workspace_id=workspace_id)
