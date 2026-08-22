from datetime import UTC, datetime, timedelta
from pathlib import Path

from pressradar.domain.analytics import ProductEvent, ProductEventName
from pressradar.infrastructure.sqlite_analytics import SQLiteAnalyticsStore


def test_sqlite_analytics_is_idempotent_and_calculates_metrics(tmp_path: Path) -> None:
    store = SQLiteAnalyticsStore(str(tmp_path / "metrics.db"))
    store.initialize()
    detected_at = datetime(2026, 8, 22, 10, tzinfo=UTC)
    events = (
        _event("one", ProductEventName.OPPORTUNITY_DETECTED, detected_at, None),
        _event("one", ProductEventName.ANALYSIS_COMPLETED, detected_at, 90),
        _event("one", ProductEventName.PITCH_APPROVED, detected_at + timedelta(minutes=5), 90),
        _event("one", ProductEventName.PITCH_SENT, detected_at + timedelta(minutes=10), 90),
        _event("two", ProductEventName.OPPORTUNITY_DETECTED, detected_at, None),
        _event("two", ProductEventName.ANALYSIS_COMPLETED, detected_at, 70),
        _event("two", ProductEventName.OPPORTUNITY_DISMISSED, detected_at, 70),
    )
    for event in (*events, events[0]):
        store.record(event)

    summary = store.summary(workspace_id="workspace-1")

    assert summary.opportunities_detected == 2
    assert summary.average_relevance_score == 80
    assert summary.average_seconds_to_review == 300
    assert summary.average_seconds_to_send == 600
    assert summary.approval_rate == 0.5
    assert summary.pitch_send_rate == 0.5
    assert summary.dismissal_rate == 0.5


def _event(
    opportunity_id: str,
    name: ProductEventName,
    occurred_at: datetime,
    relevance_score: int | None,
) -> ProductEvent:
    return ProductEvent(
        id=f"{opportunity_id}:{name.value}",
        workspace_id="workspace-1",
        name=name,
        occurred_at=occurred_at,
        opportunity_id=opportunity_id,
        client_id=f"client-{opportunity_id}",
        client_name=f"Client {opportunity_id}",
        source="Demo source",
        relevance_score=relevance_score,
        detected_at=datetime(2026, 8, 22, 10, tzinfo=UTC),
    )
