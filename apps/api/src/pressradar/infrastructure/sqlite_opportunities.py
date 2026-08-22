import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pressradar.domain.opportunities import Opportunity, OpportunityMatch, OpportunityStatus
from pressradar.domain.relevance import RelevanceAnalysis


class SQLiteOpportunityRepository:
    def __init__(self, database_path: str) -> None:
        self._database_path = database_path

    def initialize(self) -> None:
        Path(self._database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS opportunities (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                    client_id TEXT NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                    media_item_id TEXT NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
                    matched_topics TEXT NOT NULL,
                    relevance_score INTEGER,
                    relevance_reason TEXT,
                    analysis_error TEXT,
                    status TEXT NOT NULL,
                    detected_at TEXT NOT NULL,
                    UNIQUE(client_id, media_item_id)
                );
                CREATE INDEX IF NOT EXISTS idx_opportunities_workspace
                ON opportunities(workspace_id, detected_at DESC);
                """
            )
            self._add_relevance_columns(connection)

    def create_matches(self, matches: tuple[OpportunityMatch, ...]) -> int:
        created = 0
        detected_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            for match in matches:
                cursor = connection.execute(
                    """INSERT OR IGNORE INTO opportunities (
                        id, workspace_id, client_id, media_item_id, matched_topics,
                        status, detected_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(uuid4()),
                        match.workspace_id,
                        match.client_id,
                        match.media_item_id,
                        json.dumps(match.matched_topics),
                        OpportunityStatus.NEW.value,
                        detected_at,
                    ),
                )
                created += cursor.rowcount
        return created

    def list(self, *, workspace_id: str) -> list[Opportunity]:
        with self._connect() as connection:
            rows = connection.execute(
                f"{_SELECT} WHERE o.workspace_id = ? "
                "ORDER BY (m.deadline IS NULL), m.deadline, "
                "o.relevance_score DESC, o.detected_at DESC, o.id",
                (workspace_id,),
            ).fetchall()
        return [self._opportunity(row) for row in rows]

    def get(self, *, workspace_id: str, opportunity_id: str) -> Opportunity | None:
        with self._connect() as connection:
            row = connection.execute(
                f"{_SELECT} WHERE o.workspace_id = ? AND o.id = ?",
                (workspace_id, opportunity_id),
            ).fetchone()
        return None if row is None else self._opportunity(row)

    def update_status(
        self,
        *,
        workspace_id: str,
        opportunity_id: str,
        current_status: OpportunityStatus,
        new_status: OpportunityStatus,
    ) -> Opportunity | None:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE opportunities SET status = ?
                WHERE id = ? AND workspace_id = ? AND status = ?""",
                (new_status.value, opportunity_id, workspace_id, current_status.value),
            )
            if cursor.rowcount == 0:
                return None
        return self.get(workspace_id=workspace_id, opportunity_id=opportunity_id)

    def complete_analysis(
        self,
        *,
        workspace_id: str,
        opportunity_id: str,
        analysis: RelevanceAnalysis,
    ) -> Opportunity | None:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE opportunities
                SET relevance_score = ?, relevance_reason = ?, matched_topics = ?,
                    analysis_error = NULL, status = ?
                WHERE id = ? AND workspace_id = ? AND status = ?""",
                (
                    analysis.score,
                    analysis.reason,
                    json.dumps(analysis.matched_topics),
                    OpportunityStatus.READY.value,
                    opportunity_id,
                    workspace_id,
                    OpportunityStatus.ANALYZING.value,
                ),
            )
            if cursor.rowcount == 0:
                return None
        return self.get(workspace_id=workspace_id, opportunity_id=opportunity_id)

    def fail_analysis(self, *, workspace_id: str, opportunity_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """UPDATE opportunities SET status = ?, analysis_error = ?
                WHERE id = ? AND workspace_id = ? AND status = ?""",
                (
                    OpportunityStatus.FAILED.value,
                    "Relevance analysis is temporarily unavailable.",
                    opportunity_id,
                    workspace_id,
                    OpportunityStatus.ANALYZING.value,
                ),
            )

    @staticmethod
    def _opportunity(row: sqlite3.Row) -> Opportunity:
        return Opportunity(
            id=str(row["id"]),
            workspace_id=str(row["workspace_id"]),
            client_id=str(row["client_id"]),
            client_name=str(row["client_name"]),
            client_company=str(row["client_company"]),
            media_item_id=str(row["media_item_id"]),
            source=str(row["source"]),
            headline=str(row["headline"]),
            journalist=None if row["journalist"] is None else str(row["journalist"]),
            published_at=datetime.fromisoformat(str(row["published_at"])),
            deadline=(
                None if row["deadline"] is None else datetime.fromisoformat(str(row["deadline"]))
            ),
            matched_topics=tuple(json.loads(row["matched_topics"])),
            relevance_score=(
                None if row["relevance_score"] is None else int(row["relevance_score"])
            ),
            relevance_reason=(
                None if row["relevance_reason"] is None else str(row["relevance_reason"])
            ),
            analysis_error=(None if row["analysis_error"] is None else str(row["analysis_error"])),
            status=OpportunityStatus(str(row["status"])),
            detected_at=datetime.fromisoformat(str(row["detected_at"])),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _add_relevance_columns(connection: sqlite3.Connection) -> None:
        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(opportunities)").fetchall()
        }
        additions = {
            "relevance_score": "INTEGER",
            "relevance_reason": "TEXT",
            "analysis_error": "TEXT",
        }
        for name, data_type in additions.items():
            if name not in columns:
                connection.execute(f"ALTER TABLE opportunities ADD COLUMN {name} {data_type}")


_SELECT = """SELECT o.*, c.name AS client_name, c.company AS client_company,
    m.source, m.headline, m.journalist, m.published_at, m.deadline
    FROM opportunities o
    JOIN clients c ON c.id = o.client_id
    JOIN media_items m ON m.id = o.media_item_id"""
