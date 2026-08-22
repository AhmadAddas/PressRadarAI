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
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS media_items (
                    id TEXT PRIMARY KEY,
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
                    dedupe_key TEXT NOT NULL UNIQUE,
                    ingested_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_media_published ON media_items(published_at DESC);
                """
            )

    def ingest(self, items: tuple[IncomingMediaItem, ...]) -> IngestionResult:
        created = 0
        ingested_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            for item in items:
                cursor = connection.execute(
                    """INSERT OR IGNORE INTO media_items (
                        id, source, source_type, author, journalist, headline, body, url,
                        published_at, deadline, topics, external_id, dedupe_key, ingested_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(uuid4()),
                        item.source,
                        item.source_type.value,
                        item.author,
                        item.journalist,
                        item.headline,
                        item.body,
                        item.url,
                        item.published_at.isoformat(),
                        None if item.deadline is None else item.deadline.isoformat(),
                        json.dumps(item.topics),
                        item.external_id,
                        MediaIngestionService.dedupe_key(item),
                        ingested_at,
                    ),
                )
                created += cursor.rowcount
        return IngestionResult(created=created, duplicates=len(items) - created)

    def list(self, *, limit: int) -> list[MediaItem]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM media_items ORDER BY published_at DESC, id LIMIT ?", (limit,)
            ).fetchall()
        return [self._media_item(row) for row in rows]

    def get(self, *, media_item_id: str) -> MediaItem | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM media_items WHERE id = ?", (media_item_id,)
            ).fetchone()
        return None if row is None else self._media_item(row)

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
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection
