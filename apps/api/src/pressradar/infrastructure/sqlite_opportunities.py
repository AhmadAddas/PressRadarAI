import builtins
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pressradar.domain.audit import AuditAction, AuditEvent
from pressradar.domain.delivery import Delivery, DeliveryReceipt
from pressradar.domain.opportunities import Opportunity, OpportunityMatch, OpportunityStatus
from pressradar.domain.pitches import GeneratedPitch, Pitch
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
                    pitch_error TEXT,
                    display_headline TEXT,
                    send_error TEXT,
                    status TEXT NOT NULL,
                    detected_at TEXT NOT NULL,
                    UNIQUE(client_id, media_item_id)
                );
                CREATE INDEX IF NOT EXISTS idx_opportunities_workspace
                ON opportunities(workspace_id, detected_at DESC);
                CREATE TABLE IF NOT EXISTS pitches (
                    id TEXT PRIMARY KEY,
                    opportunity_id TEXT NOT NULL UNIQUE
                        REFERENCES opportunities(id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS pitch_deliveries (
                    id TEXT PRIMARY KEY,
                    opportunity_id TEXT NOT NULL UNIQUE
                        REFERENCES opportunities(id) ON DELETE CASCADE,
                    provider TEXT NOT NULL,
                    reference TEXT NOT NULL,
                    sent_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                    opportunity_id TEXT NOT NULL
                        REFERENCES opportunities(id) ON DELETE CASCADE,
                    action TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    detail TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_audit_opportunity
                ON audit_events(workspace_id, opportunity_id, occurred_at, id);
                """
            )
            self._add_relevance_columns(connection)

    def create_matches(self, matches: tuple[OpportunityMatch, ...]) -> int:
        created = 0
        detected_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            for match in matches:
                opportunity_id = str(uuid4())
                cursor = connection.execute(
                    """INSERT OR IGNORE INTO opportunities (
                        id, workspace_id, client_id, media_item_id, matched_topics,
                        status, detected_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        opportunity_id,
                        match.workspace_id,
                        match.client_id,
                        match.media_item_id,
                        json.dumps(match.matched_topics),
                        OpportunityStatus.NEW.value,
                        detected_at,
                    ),
                )
                created += cursor.rowcount
                if cursor.rowcount:
                    self._audit(
                        connection,
                        workspace_id=match.workspace_id,
                        opportunity_id=opportunity_id,
                        action=AuditAction.OPPORTUNITY_DETECTED,
                        occurred_at=detected_at,
                    )
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

    def delete(self, *, workspace_id: str, opportunity_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM opportunities WHERE id = ? AND workspace_id = ?",
                (opportunity_id, workspace_id),
            )
        return cursor.rowcount > 0

    def clear(self, *, workspace_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM opportunities WHERE workspace_id = ?", (workspace_id,))

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
            audit_action = {
                OpportunityStatus.ANALYZING: AuditAction.ANALYSIS_STARTED,
                OpportunityStatus.DISMISSED: AuditAction.OPPORTUNITY_DISMISSED,
            }.get(new_status)
            if audit_action is not None:
                self._audit(
                    connection,
                    workspace_id=workspace_id,
                    opportunity_id=opportunity_id,
                    action=audit_action,
                )
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
            self._audit(
                connection,
                workspace_id=workspace_id,
                opportunity_id=opportunity_id,
                action=AuditAction.ANALYSIS_COMPLETED,
            )
        return self.get(workspace_id=workspace_id, opportunity_id=opportunity_id)

    def fail_analysis(self, *, workspace_id: str, opportunity_id: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
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
            if cursor.rowcount:
                self._audit(
                    connection,
                    workspace_id=workspace_id,
                    opportunity_id=opportunity_id,
                    action=AuditAction.PROCESSING_FAILED,
                    detail="Relevance analysis failed",
                )

    def save_generated_pitch(
        self,
        *,
        workspace_id: str,
        opportunity_id: str,
        pitch: GeneratedPitch,
    ) -> Opportunity | None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT OR IGNORE INTO pitches (
                    id, opportunity_id, content, generated_at, updated_at
                ) SELECT ?, o.id, ?, ?, ? FROM opportunities o
                WHERE o.id = ? AND o.workspace_id = ? AND o.status = ?""",
                (
                    str(uuid4()),
                    pitch.content,
                    now,
                    now,
                    opportunity_id,
                    workspace_id,
                    OpportunityStatus.READY.value,
                ),
            )
            if cursor.rowcount == 0:
                return None
            connection.execute(
                "UPDATE opportunities SET display_headline = ?, pitch_error = NULL WHERE id = ?",
                (pitch.display_headline, opportunity_id),
            )
            self._audit(
                connection,
                workspace_id=workspace_id,
                opportunity_id=opportunity_id,
                action=AuditAction.PITCH_GENERATED,
            )
        return self.get(workspace_id=workspace_id, opportunity_id=opportunity_id)

    def fail_pitch_generation(self, *, workspace_id: str, opportunity_id: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE opportunities SET pitch_error = ?
                WHERE id = ? AND workspace_id = ? AND status = ?
                AND NOT EXISTS (
                    SELECT 1 FROM pitches WHERE opportunity_id = opportunities.id
                )""",
                (
                    "Pitch generation is temporarily unavailable.",
                    opportunity_id,
                    workspace_id,
                    OpportunityStatus.READY.value,
                ),
            )
            if cursor.rowcount:
                self._audit(
                    connection,
                    workspace_id=workspace_id,
                    opportunity_id=opportunity_id,
                    action=AuditAction.PROCESSING_FAILED,
                    detail="Pitch generation failed",
                )

    def update_pitch(
        self,
        *,
        workspace_id: str,
        opportunity_id: str,
        content: str,
    ) -> Opportunity | None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            opportunity = connection.execute(
                "SELECT status FROM opportunities WHERE id = ? AND workspace_id = ?",
                (opportunity_id, workspace_id),
            ).fetchone()
            if opportunity is None or opportunity["status"] != OpportunityStatus.READY.value:
                return None
            connection.execute(
                """INSERT INTO pitches (id, opportunity_id, content, generated_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(opportunity_id) DO UPDATE
                SET content = excluded.content, updated_at = excluded.updated_at""",
                (str(uuid4()), opportunity_id, content, now, now),
            )
            connection.execute(
                "UPDATE opportunities SET pitch_error = NULL WHERE id = ?",
                (opportunity_id,),
            )
            self._audit(
                connection,
                workspace_id=workspace_id,
                opportunity_id=opportunity_id,
                action=AuditAction.PITCH_EDITED,
            )
        return self.get(workspace_id=workspace_id, opportunity_id=opportunity_id)

    def approve(self, *, workspace_id: str, opportunity_id: str) -> Opportunity | None:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE opportunities SET status = ?
                WHERE id = ? AND workspace_id = ? AND status = ?
                AND EXISTS (SELECT 1 FROM pitches WHERE opportunity_id = opportunities.id)""",
                (
                    OpportunityStatus.APPROVED.value,
                    opportunity_id,
                    workspace_id,
                    OpportunityStatus.READY.value,
                ),
            )
            if cursor.rowcount == 0:
                return None
            self._audit(
                connection,
                workspace_id=workspace_id,
                opportunity_id=opportunity_id,
                action=AuditAction.PITCH_APPROVED,
            )
        return self.get(workspace_id=workspace_id, opportunity_id=opportunity_id)

    def claim_send(self, *, workspace_id: str, opportunity_id: str) -> Opportunity | None:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE opportunities SET status = ?, send_error = NULL
                WHERE id = ? AND workspace_id = ? AND status = ?
                AND EXISTS (SELECT 1 FROM pitches WHERE opportunity_id = opportunities.id)
                AND NOT EXISTS (
                    SELECT 1 FROM pitch_deliveries
                    WHERE opportunity_id = opportunities.id
                )""",
                (
                    OpportunityStatus.SENDING.value,
                    opportunity_id,
                    workspace_id,
                    OpportunityStatus.APPROVED.value,
                ),
            )
            if cursor.rowcount == 0:
                return None
        return self.get(workspace_id=workspace_id, opportunity_id=opportunity_id)

    def complete_send(
        self,
        *,
        workspace_id: str,
        opportunity_id: str,
        receipt: DeliveryReceipt,
    ) -> Opportunity | None:
        sent_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            opportunity = connection.execute(
                "SELECT status FROM opportunities WHERE id = ? AND workspace_id = ?",
                (opportunity_id, workspace_id),
            ).fetchone()
            if opportunity is None or opportunity["status"] != OpportunityStatus.SENDING.value:
                return None
            connection.execute(
                """INSERT INTO pitch_deliveries (
                    id, opportunity_id, provider, reference, sent_at
                ) VALUES (?, ?, ?, ?, ?)""",
                (
                    str(uuid4()),
                    opportunity_id,
                    receipt.provider,
                    receipt.reference,
                    sent_at,
                ),
            )
            connection.execute(
                "UPDATE opportunities SET status = ?, send_error = NULL WHERE id = ?",
                (OpportunityStatus.SENT.value, opportunity_id),
            )
            self._audit(
                connection,
                workspace_id=workspace_id,
                opportunity_id=opportunity_id,
                action=AuditAction.PITCH_SENT,
                occurred_at=sent_at,
            )
        return self.get(workspace_id=workspace_id, opportunity_id=opportunity_id)

    def fail_send(self, *, workspace_id: str, opportunity_id: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE opportunities SET status = ?, send_error = ?
                WHERE id = ? AND workspace_id = ? AND status = ?""",
                (
                    OpportunityStatus.APPROVED.value,
                    "Simulated delivery failed. The approved pitch can be retried.",
                    opportunity_id,
                    workspace_id,
                    OpportunityStatus.SENDING.value,
                ),
            )
            if cursor.rowcount:
                self._audit(
                    connection,
                    workspace_id=workspace_id,
                    opportunity_id=opportunity_id,
                    action=AuditAction.SEND_FAILED,
                )

    def list_audit(self, *, workspace_id: str, opportunity_id: str) -> builtins.list[AuditEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT id, opportunity_id, action, occurred_at, detail
                FROM audit_events WHERE workspace_id = ? AND opportunity_id = ?
                ORDER BY rowid""",
                (workspace_id, opportunity_id),
            ).fetchall()
        return [
            AuditEvent(
                id=str(row["id"]),
                opportunity_id=str(row["opportunity_id"]),
                action=AuditAction(str(row["action"])),
                occurred_at=datetime.fromisoformat(str(row["occurred_at"])),
                detail=None if row["detail"] is None else str(row["detail"]),
            )
            for row in rows
        ]

    def record_integration_failure(
        self, *, workspace_id: str, opportunity_id: str, detail: str
    ) -> None:
        with self._connect() as connection:
            visible = connection.execute(
                "SELECT 1 FROM opportunities WHERE id = ? AND workspace_id = ?",
                (opportunity_id, workspace_id),
            ).fetchone()
            if visible is not None:
                self._audit(
                    connection,
                    workspace_id=workspace_id,
                    opportunity_id=opportunity_id,
                    action=AuditAction.INTEGRATION_SYNC_FAILED,
                    detail=detail,
                )

    @staticmethod
    def _opportunity(row: sqlite3.Row) -> Opportunity:
        return Opportunity(
            id=str(row["id"]),
            workspace_id=str(row["workspace_id"]),
            client_id=str(row["client_id"]),
            client_name=str(row["client_name"]),
            client_company=str(row["client_company"]),
            client_deleted=bool(row["client_deleted"]),
            media_item_id=str(row["media_item_id"]),
            source=str(row["source"]),
            headline=str(row["headline"]),
            display_headline=(
                None if row["display_headline"] is None else str(row["display_headline"])
            ),
            media_deleted=bool(row["media_deleted"]),
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
            pitch=(
                None
                if row["pitch_id"] is None
                else Pitch(
                    id=str(row["pitch_id"]),
                    opportunity_id=str(row["id"]),
                    content=str(row["pitch_content"]),
                    generated_at=datetime.fromisoformat(str(row["pitch_generated_at"])),
                    updated_at=datetime.fromisoformat(str(row["pitch_updated_at"])),
                )
            ),
            pitch_error=None if row["pitch_error"] is None else str(row["pitch_error"]),
            delivery=(
                None
                if row["delivery_provider"] is None
                else Delivery(
                    provider=str(row["delivery_provider"]),
                    reference=str(row["delivery_reference"]),
                    sent_at=datetime.fromisoformat(str(row["delivery_sent_at"])),
                )
            ),
            send_error=None if row["send_error"] is None else str(row["send_error"]),
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
            "pitch_error": "TEXT",
            "display_headline": "TEXT",
            "send_error": "TEXT",
        }
        for name, data_type in additions.items():
            if name not in columns:
                connection.execute(f"ALTER TABLE opportunities ADD COLUMN {name} {data_type}")

    @staticmethod
    def _audit(
        connection: sqlite3.Connection,
        *,
        workspace_id: str,
        opportunity_id: str,
        action: AuditAction,
        occurred_at: str | None = None,
        detail: str | None = None,
    ) -> None:
        connection.execute(
            """INSERT INTO audit_events (
                id, workspace_id, opportunity_id, action, occurred_at, detail
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                str(uuid4()),
                workspace_id,
                opportunity_id,
                action.value,
                occurred_at or datetime.now(UTC).isoformat(),
                detail,
            ),
        )


_SELECT = """SELECT o.*, c.name AS client_name, c.company AS client_company,
    (c.deleted_at IS NOT NULL) AS client_deleted,
    m.source, m.headline, m.journalist, m.published_at, m.deadline,
    (m.deleted_at IS NOT NULL) AS media_deleted,
    p.id AS pitch_id, p.content AS pitch_content,
    p.generated_at AS pitch_generated_at, p.updated_at AS pitch_updated_at,
    d.provider AS delivery_provider, d.reference AS delivery_reference,
    d.sent_at AS delivery_sent_at
    FROM opportunities o
    JOIN clients c ON c.id = o.client_id
    JOIN media_items m ON m.id = o.media_item_id
    LEFT JOIN pitches p ON p.opportunity_id = o.id
    LEFT JOIN pitch_deliveries d ON d.opportunity_id = o.id"""
