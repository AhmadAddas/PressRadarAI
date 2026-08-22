from typing import Any, cast

from google.api_core.exceptions import GoogleAPICallError
from google.cloud import bigquery

from pressradar.application.analytics import AnalyticsError
from pressradar.domain.analytics import AnalyticsSummary, ProductEvent
from pressradar.infrastructure.sqlite_analytics import _summarize


class BigQueryAnalyticsStore:
    """Best-effort product event storage isolated from operational persistence."""

    def __init__(self, *, project: str, dataset: str, table: str) -> None:
        self._client = bigquery.Client(project=project)
        self._table = f"{project}.{dataset}.{table}"

    def record(self, event: ProductEvent) -> None:
        row = {
            "id": event.id,
            "workspace_id": event.workspace_id,
            "name": event.name.value,
            "occurred_at": event.occurred_at.isoformat(),
            "opportunity_id": event.opportunity_id,
            "client_id": event.client_id,
            "client_name": event.client_name,
            "source": event.source,
            "relevance_score": event.relevance_score,
            "detected_at": event.detected_at.isoformat(),
        }
        try:
            errors = self._client.insert_rows_json(self._table, [row], row_ids=[event.id])
        except GoogleAPICallError as error:
            raise AnalyticsError("Analytics event write failed") from error
        if errors:
            raise AnalyticsError("Analytics event write failed")

    def summary(self, *, workspace_id: str) -> AnalyticsSummary:
        query = f"""SELECT id, workspace_id, name, occurred_at, opportunity_id,
            client_id, client_name, source, relevance_score, detected_at
            FROM `{self._table}` WHERE workspace_id = @workspace_id
            ORDER BY occurred_at, id"""
        configuration = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("workspace_id", "STRING", workspace_id)]
        )
        try:
            rows = [
                dict(row.items()) for row in self._client.query(query, job_config=configuration)
            ]
            return _summarize(cast(Any, rows))
        except (GoogleAPICallError, ValueError) as error:
            raise AnalyticsError("Analytics reporting failed") from error
