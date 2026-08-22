import sqlite3
from pathlib import Path
from uuid import uuid4

from pressradar.application.media_sources import DuplicateMediaSourceError
from pressradar.domain.media_sources import MediaSource, MediaSourceDetails, MediaSourceKind


class SQLiteMediaSourceRepository:
    def __init__(self, database_path: str) -> None:
        self._database_path = database_path

    def initialize(self) -> None:
        Path(self._database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS media_sources (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK (kind IN ('rss', 'api')),
                    url TEXT,
                    provider TEXT,
                    UNIQUE (workspace_id, name)
                );
                CREATE INDEX IF NOT EXISTS idx_media_sources_workspace_kind
                    ON media_sources(workspace_id, kind, name);
                """
            )

    def create(self, *, workspace_id: str, details: MediaSourceDetails) -> MediaSource:
        source_id = str(uuid4())
        try:
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO media_sources (id, workspace_id, name, kind, url, provider)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        source_id,
                        workspace_id,
                        details.name,
                        details.kind.value,
                        details.url,
                        details.provider,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise DuplicateMediaSourceError from error
        return MediaSource(source_id, workspace_id, **vars(details))

    def list(self, *, workspace_id: str, kind: MediaSourceKind | None) -> list[MediaSource]:
        query = "SELECT * FROM media_sources WHERE workspace_id = ?"
        parameters: tuple[str, ...] = (workspace_id,)
        if kind is not None:
            query += " AND kind = ?"
            parameters += (kind.value,)
        query += " ORDER BY name COLLATE NOCASE, id"
        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._source(row) for row in rows]

    def delete(self, *, workspace_id: str, source_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM media_sources WHERE id = ? AND workspace_id = ?",
                (source_id, workspace_id),
            )
        return cursor.rowcount == 1

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _source(row: sqlite3.Row) -> MediaSource:
        return MediaSource(
            id=str(row["id"]),
            workspace_id=str(row["workspace_id"]),
            name=str(row["name"]),
            kind=MediaSourceKind(str(row["kind"])),
            url=None if row["url"] is None else str(row["url"]),
            provider=None if row["provider"] is None else str(row["provider"]),
        )
