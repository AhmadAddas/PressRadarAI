import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pressradar.application.media import MediaIngestionService
from pressradar.domain.media import IncomingMediaItem, IngestionResult, MediaItem, MediaSourceType


class SQLiteMediaRepository:
    def __init__(self, database_path: str) -> None:
        self._database_path = database_path

    def initialize(self) -> None:
        Path(self._database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(media_items)").fetchall()
            }
            if columns and "workspace_id" not in columns:
                self._migrate_workspace_media(connection)
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS media_items (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                    source TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    author TEXT,
                    journalist TEXT,
                    headline TEXT NOT NULL,
                    display_headline TEXT,
                    body TEXT NOT NULL,
                    url TEXT,
                    published_at TEXT NOT NULL,
                    deadline TEXT,
                    topics TEXT NOT NULL,
                    external_id TEXT,
                    dedupe_key TEXT NOT NULL,
                    ingested_at TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_media_workspace_dedupe
                    ON media_items(workspace_id, dedupe_key);
                CREATE INDEX IF NOT EXISTS idx_media_published ON media_items(published_at DESC);
                """
            )
            self._add_deleted_column(connection)
            self._add_display_headline_column(connection)

    @staticmethod
    def _migrate_workspace_media(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            ALTER TABLE media_items RENAME TO legacy_media_items;
            CREATE TABLE media_items (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                source TEXT NOT NULL,
                source_type TEXT NOT NULL,
                author TEXT,
                journalist TEXT,
                headline TEXT NOT NULL,
                body TEXT NOT NULL,
                url TEXT,
                published_at TEXT NOT NULL,
                deadline TEXT,
                topics TEXT NOT NULL,
                external_id TEXT,
                dedupe_key TEXT NOT NULL,
                ingested_at TEXT NOT NULL
            );
            INSERT INTO media_items (
                id, workspace_id, source, source_type, author, journalist, headline, body,
                url, published_at, deadline, topics, external_id, dedupe_key, ingested_at
            )
            SELECT w.id || ':' || m.id, w.id, m.source, m.source_type, m.author,
                m.journalist, m.headline, m.body, m.url, m.published_at, m.deadline,
                m.topics, m.external_id, m.dedupe_key, m.ingested_at
            FROM legacy_media_items AS m CROSS JOIN workspaces AS w;
            UPDATE opportunities
            SET media_item_id = workspace_id || ':' || media_item_id;
            DROP TABLE legacy_media_items;
            """
        )

    def ingest(self, *, workspace_id: str, items: tuple[IncomingMediaItem, ...]) -> IngestionResult:
        created = 0
        restored = 0
        ingested_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            for item in items:
                dedupe_key = MediaIngestionService.dedupe_key(item)
                restore = connection.execute(
                    """UPDATE media_items SET deleted_at = NULL, source = ?, source_type = ?,
                        author = ?, journalist = ?, headline = ?, body = ?, url = ?,
                        display_headline = ?, published_at = ?, deadline = ?, topics = ?,
                        external_id = ?, ingested_at = ?
                    WHERE workspace_id = ? AND dedupe_key = ? AND deleted_at IS NOT NULL""",
                    (
                        item.source,
                        item.source_type.value,
                        item.author,
                        item.journalist,
                        item.headline,
                        item.body,
                        item.url,
                        item.display_headline,
                        item.published_at.isoformat(),
                        None if item.deadline is None else item.deadline.isoformat(),
                        json.dumps(item.topics),
                        item.external_id,
                        ingested_at,
                        workspace_id,
                        dedupe_key,
                    ),
                )
                if restore.rowcount:
                    restored += 1
                    continue
                connection.execute(
                    """UPDATE media_items SET display_headline = ?
                    WHERE workspace_id = ? AND dedupe_key = ? AND deleted_at IS NULL
                        AND display_headline IS NULL""",
                    (item.display_headline, workspace_id, dedupe_key),
                )
                cursor = connection.execute(
                    """INSERT OR IGNORE INTO media_items (
                        id, workspace_id, source, source_type, author, journalist,
                        headline, body, url,
                        display_headline, published_at, deadline, topics, external_id,
                        dedupe_key, ingested_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(uuid4()),
                        workspace_id,
                        item.source,
                        item.source_type.value,
                        item.author,
                        item.journalist,
                        item.headline,
                        item.body,
                        item.url,
                        item.display_headline,
                        item.published_at.isoformat(),
                        None if item.deadline is None else item.deadline.isoformat(),
                        json.dumps(item.topics),
                        item.external_id,
                        dedupe_key,
                        ingested_at,
                    ),
                )
                created += cursor.rowcount
        return IngestionResult(
            created=created,
            restored=restored,
            duplicates=len(items) - created - restored,
        )

    def list(self, *, workspace_id: str, limit: int) -> list[MediaItem]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM media_items WHERE workspace_id = ? AND deleted_at IS NULL
                ORDER BY published_at DESC, id LIMIT ?""",
                (workspace_id, limit),
            ).fetchall()
        return [self._media_item(row) for row in rows]

    def get(self, *, workspace_id: str, media_item_id: str) -> MediaItem | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM media_items
                WHERE id = ? AND workspace_id = ? AND deleted_at IS NULL""",
                (media_item_id, workspace_id),
            ).fetchone()
        return None if row is None else self._media_item(row)

    def delete(self, *, workspace_id: str, media_item_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE media_items SET deleted_at = CURRENT_TIMESTAMP
                WHERE id = ? AND workspace_id = ? AND deleted_at IS NULL""",
                (media_item_id, workspace_id),
            )
        return cursor.rowcount > 0

    def update_deadline(
        self, *, workspace_id: str, media_item_id: str, deadline: datetime | None
    ) -> MediaItem | None:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE media_items SET deadline = ?
                WHERE id = ? AND workspace_id = ? AND deleted_at IS NULL""",
                (
                    None if deadline is None else deadline.isoformat(),
                    media_item_id,
                    workspace_id,
                ),
            )
        if not cursor.rowcount:
            return None
        return self.get(workspace_id=workspace_id, media_item_id=media_item_id)

    def clear(self, *, workspace_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM media_items WHERE workspace_id = ?", (workspace_id,))

    @staticmethod
    def _add_deleted_column(connection: sqlite3.Connection) -> None:
        columns = {str(row["name"]) for row in connection.execute("PRAGMA table_info(media_items)")}
        if "deleted_at" not in columns:
            connection.execute("ALTER TABLE media_items ADD COLUMN deleted_at TEXT")

    @staticmethod
    def _add_display_headline_column(connection: sqlite3.Connection) -> None:
        columns = {str(row["name"]) for row in connection.execute("PRAGMA table_info(media_items)")}
        if "display_headline" not in columns:
            connection.execute("ALTER TABLE media_items ADD COLUMN display_headline TEXT")

    @staticmethod
    def _media_item(row: sqlite3.Row) -> MediaItem:
        return MediaItem(
            id=str(row["id"]),
            source=str(row["source"]),
            source_type=MediaSourceType(str(row["source_type"])),
            author=None if row["author"] is None else str(row["author"]),
            journalist=None if row["journalist"] is None else str(row["journalist"]),
            headline=str(row["headline"]),
            body=str(row["body"]),
            url=None if row["url"] is None else str(row["url"]),
            published_at=datetime.fromisoformat(str(row["published_at"])),
            deadline=(
                None if row["deadline"] is None else datetime.fromisoformat(str(row["deadline"]))
            ),
            topics=tuple(json.loads(row["topics"])),
            external_id=None if row["external_id"] is None else str(row["external_id"]),
            ingested_at=datetime.fromisoformat(str(row["ingested_at"])),
            display_headline=(
                None if row["display_headline"] is None else str(row["display_headline"])
            ),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection
