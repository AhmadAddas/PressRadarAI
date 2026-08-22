import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from pressradar.application.analytics import AnalyticsError
from pressradar.domain.analytics import (
    AnalyticsSummary,
    ClientVolume,
    ProductEvent,
    ProductEventName,
    SourcePerformance,
)


class SQLiteAnalyticsStore:
    def __init__(self, database_path: str) -> None:
        self._database_path = database_path

    def initialize(self) -> None:
        try:
            Path(self._database_path).parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS product_events (
                        id TEXT PRIMARY KEY,
                        workspace_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        occurred_at TEXT NOT NULL,
                        opportunity_id TEXT NOT NULL,
                        client_id TEXT NOT NULL,
                        client_name TEXT NOT NULL,
                        source TEXT NOT NULL,
                        relevance_score INTEGER,
                        detected_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_product_events_workspace
                    ON product_events(workspace_id, occurred_at, id);
                    """
                )
        except (OSError, sqlite3.Error) as error:
            raise AnalyticsError("Analytics initialization failed") from error

    def record(self, event: ProductEvent) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    """INSERT OR IGNORE INTO product_events (
                        id, workspace_id, name, occurred_at, opportunity_id,
                        client_id, client_name, source, relevance_score, detected_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        event.id,
                        event.workspace_id,
                        event.name.value,
                        event.occurred_at.isoformat(),
                        event.opportunity_id,
                        event.client_id,
                        event.client_name,
                        event.source,
                        event.relevance_score,
                        event.detected_at.isoformat(),
                    ),
                )
        except sqlite3.Error as error:
            raise AnalyticsError("Analytics event write failed") from error

    def summary(self, *, workspace_id: str) -> AnalyticsSummary:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    """SELECT * FROM product_events
                    WHERE workspace_id = ? ORDER BY occurred_at, id""",
                    (workspace_id,),
                ).fetchall()
            return _summarize(rows)
        except (sqlite3.Error, ValueError) as error:
            raise AnalyticsError("Analytics reporting failed") from error

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection


def _summarize(rows: list[sqlite3.Row]) -> AnalyticsSummary:
    detected: dict[str, sqlite3.Row] = {}
    scores: dict[str, int] = {}
    reviewed: dict[str, datetime] = {}
    approved: set[str] = set()
    sent: dict[str, datetime] = {}
    dismissed: set[str] = set()
    for row in rows:
        opportunity_id = str(row["opportunity_id"])
        name = ProductEventName(str(row["name"]))
        occurred_at = datetime.fromisoformat(str(row["occurred_at"]))
        if name is ProductEventName.OPPORTUNITY_DETECTED:
            detected.setdefault(opportunity_id, row)
        elif name is ProductEventName.ANALYSIS_COMPLETED and row["relevance_score"] is not None:
            scores[opportunity_id] = int(row["relevance_score"])
        elif name in {ProductEventName.PITCH_REVIEWED, ProductEventName.PITCH_APPROVED}:
            reviewed.setdefault(opportunity_id, occurred_at)
            if name is ProductEventName.PITCH_APPROVED:
                approved.add(opportunity_id)
        elif name is ProductEventName.PITCH_SENT:
            sent.setdefault(opportunity_id, occurred_at)
        elif name is ProductEventName.OPPORTUNITY_DISMISSED:
            dismissed.add(opportunity_id)

    total = len(detected)
    source_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    client_counts: dict[tuple[str, str], int] = defaultdict(int)
    for opportunity_id, row in detected.items():
        source = str(row["source"])
        source_counts[source][0] += 1
        source_counts[source][1] += opportunity_id in sent
        client_counts[(str(row["client_id"]), str(row["client_name"]))] += 1

    review_seconds = _durations(detected, reviewed)
    send_seconds = _durations(detected, sent)
    return AnalyticsSummary(
        opportunities_detected=total,
        average_relevance_score=_average(list(scores.values())),
        average_seconds_to_review=_average(review_seconds),
        average_seconds_to_send=_average(send_seconds),
        approval_rate=_rate(len(approved), total),
        pitch_send_rate=_rate(len(sent), total),
        dismissal_rate=_rate(len(dismissed), total),
        sources=tuple(
            SourcePerformance(source=source, opportunities=counts[0], sent=counts[1])
            for source, counts in sorted(source_counts.items())
        ),
        clients=tuple(
            ClientVolume(client_id=client_id, client_name=client_name, opportunities=count)
            for (client_id, client_name), count in sorted(
                client_counts.items(), key=lambda item: (-item[1], item[0][1].casefold())
            )
        ),
    )


def _durations(detected: dict[str, sqlite3.Row], completed: dict[str, datetime]) -> list[float]:
    return [
        max(
            0,
            (
                completed_at - datetime.fromisoformat(str(detected[opportunity_id]["detected_at"]))
            ).total_seconds(),
        )
        for opportunity_id, completed_at in completed.items()
        if opportunity_id in detected
    ]


def _average(values: list[int] | list[float]) -> float | None:
    return None if not values else round(sum(values) / len(values), 2)


def _rate(count: int, total: int) -> float:
    return 0 if total == 0 else round(count / total, 4)
