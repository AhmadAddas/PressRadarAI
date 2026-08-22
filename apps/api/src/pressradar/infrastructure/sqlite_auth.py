import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from pressradar.application.auth import DuplicateEmailError
from pressradar.domain.auth import Identity


class SQLiteAuthRepository:
    def __init__(self, database_path: str) -> None:
        self._database_path = database_path

    def initialize(self) -> None:
        path = Path(self._database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                PRAGMA foreign_keys = ON;
                CREATE TABLE IF NOT EXISTS workspaces (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
                    email TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    password_hash TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    expires_at TEXT NOT NULL
                );
                """
            )

    def create_identity(self, *, email: str, name: str, password_hash: str) -> Identity:
        user_id = str(uuid4())
        workspace_id = str(uuid4())
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO workspaces (id, name) VALUES (?, ?)",
                    (workspace_id, f"{name}'s workspace"),
                )
                connection.execute(
                    """INSERT INTO users (id, workspace_id, email, name, password_hash)
                    VALUES (?, ?, ?, ?, ?)""",
                    (user_id, workspace_id, email, name, password_hash),
                )
        except sqlite3.IntegrityError as error:
            raise DuplicateEmailError from error
        return Identity(user_id=user_id, workspace_id=workspace_id, email=email, name=name)

    def find_credentials(self, email: str) -> tuple[Identity, str] | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT id, workspace_id, email, name, password_hash
                FROM users WHERE email = ?""",
                (email,),
            ).fetchone()
        if row is None:
            return None
        return self._identity(row), str(row["password_hash"])

    def create_session(self, *, token_hash: str, user_id: str, expires_at: datetime) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (token_hash, user_id, expires_at.isoformat()),
            )

    def find_identity_by_session(self, *, token_hash: str, now: datetime) -> Identity | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT users.id, users.workspace_id, users.email, users.name
                FROM sessions JOIN users ON users.id = sessions.user_id
                WHERE sessions.token_hash = ? AND sessions.expires_at > ?""",
                (token_hash, now.isoformat()),
            ).fetchone()
        return None if row is None else self._identity(row)

    def delete_session(self, token_hash: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _identity(row: sqlite3.Row) -> Identity:
        return Identity(
            user_id=str(row["id"]),
            workspace_id=str(row["workspace_id"]),
            email=str(row["email"]),
            name=str(row["name"]),
        )
