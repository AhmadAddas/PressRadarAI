from pressradar.domain.analytics import AnalyticsSummary, ProductEvent


class NoOpAnalyticsStore:
    def record(self, event: ProductEvent) -> None:
        pass

    def summary(self, *, workspace_id: str) -> AnalyticsSummary:
        return AnalyticsSummary(
            opportunities_detected=0,
            average_relevance_score=None,
            average_seconds_to_review=None,
            average_seconds_to_send=None,
            approval_rate=0,
            pitch_send_rate=0,
            dismissal_rate=0,
            sources=(),
            clients=(),
        )
