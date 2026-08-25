import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from pressradar.application.auth import DuplicateEmailError
from pressradar.domain.auth import Identity, WorkspaceKind


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
                    password_hash TEXT NOT NULL,
                    totp_secret TEXT,
                    totp_enabled INTEGER NOT NULL DEFAULT 0,
                    onboarding_completed INTEGER NOT NULL DEFAULT 0,
                    email_verified INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    expires_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workspace_memberships (
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL CHECK (kind IN ('prod', 'demo')),
                    PRIMARY KEY (user_id, kind),
                    UNIQUE (workspace_id)
                );
                CREATE TABLE IF NOT EXISTS email_otp_challenges (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    purpose TEXT NOT NULL,
                    code_hash TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    consumed_at TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            self._migrate_workspace_memberships(connection)
            self._migrate_security_columns(connection)
            challenge_columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(email_otp_challenges)").fetchall()
            }
            if "attempts" not in challenge_columns:
                connection.execute(
                    "ALTER TABLE email_otp_challenges ADD COLUMN attempts "
                    "INTEGER NOT NULL DEFAULT 0"
                )

    def create_identity(
        self, *, email: str, name: str, password_hash: str, email_verified: bool
    ) -> Identity:
        user_id = str(uuid4())
        workspace_id = str(uuid4())
        demo_workspace_id = str(uuid4())
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO workspaces (id, name) VALUES (?, ?)",
                    (workspace_id, f"{name}'s Prod workspace"),
                )
                connection.execute(
                    "INSERT INTO workspaces (id, name) VALUES (?, ?)",
                    (demo_workspace_id, f"{name}'s Demo workspace"),
                )
                connection.execute(
                    """INSERT INTO users
                    (id, workspace_id, email, name, password_hash, email_verified)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (user_id, workspace_id, email, name, password_hash, int(email_verified)),
                )
                connection.executemany(
                    """INSERT INTO workspace_memberships (user_id, workspace_id, kind)
                    VALUES (?, ?, ?)""",
                    (
                        (user_id, workspace_id, WorkspaceKind.PROD.value),
                        (user_id, demo_workspace_id, WorkspaceKind.DEMO.value),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise DuplicateEmailError from error
        return Identity(user_id=user_id, workspace_id=workspace_id, email=email, name=name)

    def find_credentials(self, email: str) -> tuple[Identity, str] | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT id, workspace_id, email, name, password_hash,
                    totp_enabled, onboarding_completed
                FROM users WHERE email = ? AND email_verified = 1""",
                (email,),
            ).fetchone()
        if row is None:
            return None
        return self._identity(row), str(row["password_hash"])

    def find_identity(self, user_id: str) -> Identity | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT id, workspace_id, email, name, totp_enabled,
                    onboarding_completed FROM users WHERE id = ?""",
                (user_id,),
            ).fetchone()
        return None if row is None else self._identity(row)

    def verify_email(self, user_id: str) -> None:
        with self._connect() as connection:
            connection.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (user_id,))

    def delete_unverified_identity(self, user_id: str) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT workspace_id FROM users WHERE id = ? AND email_verified = 0", (user_id,)
            ).fetchone()
            if row is None:
                return
            workspace_ids = [
                str(item["workspace_id"])
                for item in connection.execute(
                    "SELECT workspace_id FROM workspace_memberships WHERE user_id = ?", (user_id,)
                ).fetchall()
            ]
            connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
            connection.executemany(
                "DELETE FROM workspaces WHERE id = ?", ((item,) for item in workspace_ids)
            )

    def create_session(self, *, token_hash: str, user_id: str, expires_at: datetime) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (token_hash, user_id, expires_at.isoformat()),
            )

    def find_identity_by_session(
        self, *, token_hash: str, now: datetime, workspace_kind: WorkspaceKind
    ) -> Identity | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT users.id, memberships.workspace_id, users.email, users.name,
                    users.totp_enabled, users.onboarding_completed,
                    memberships.kind AS workspace_kind
                FROM sessions JOIN users ON users.id = sessions.user_id
                JOIN workspace_memberships AS memberships ON memberships.user_id = users.id
                WHERE sessions.token_hash = ? AND sessions.expires_at > ?
                    AND memberships.kind = ?""",
                (token_hash, now.isoformat(), workspace_kind.value),
            ).fetchone()
        return None if row is None else self._identity(row)

    def delete_session(self, token_hash: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))

    def get_security(self, user_id: str) -> tuple[str | None, bool]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT totp_secret, totp_enabled FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        if row is None:
            return None, False
        return (
            None if row["totp_secret"] is None else str(row["totp_secret"]),
            bool(row["totp_enabled"]),
        )

    def save_totp(self, *, user_id: str, secret: str, enabled: bool) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE users SET totp_secret = ?, totp_enabled = ? WHERE id = ?",
                (secret, int(enabled), user_id),
            )

    def complete_onboarding(self, user_id: str) -> None:
        with self._connect() as connection:
            connection.execute("UPDATE users SET onboarding_completed = 1 WHERE id = ?", (user_id,))

    def update_password(self, *, user_id: str, password_hash: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id)
            )

    def save_email_challenge(
        self,
        *,
        challenge_id: str,
        user_id: str,
        purpose: str,
        code_hash: str,
        expires_at: datetime,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO email_otp_challenges
                (id, user_id, purpose, code_hash, expires_at)
                VALUES (?, ?, ?, ?, ?)""",
                (challenge_id, user_id, purpose, code_hash, expires_at.isoformat()),
            )

    def consume_email_challenge(
        self,
        *,
        challenge_id: str,
        user_id: str,
        purpose: str,
        code_hash: str,
        now: datetime,
    ) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT code_hash, expires_at, consumed_at, attempts
                FROM email_otp_challenges WHERE id = ? AND user_id = ? AND purpose = ?""",
                (challenge_id, user_id, purpose),
            ).fetchone()
            if (
                row is None
                or row["consumed_at"] is not None
                or int(row["attempts"]) >= 5
                or str(row["expires_at"]) <= now.isoformat()
            ):
                return False
            if str(row["code_hash"]) != code_hash:
                connection.execute(
                    "UPDATE email_otp_challenges SET attempts = attempts + 1 WHERE id = ?",
                    (challenge_id,),
                )
                return False
            connection.execute(
                "UPDATE email_otp_challenges SET consumed_at = ? WHERE id = ?",
                (now.isoformat(), challenge_id),
            )
            return True

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _migrate_security_columns(connection: sqlite3.Connection) -> None:
        columns = {
            str(row["name"]) for row in connection.execute("PRAGMA table_info(users)").fetchall()
        }
        if "totp_secret" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN totp_secret TEXT")
        if "totp_enabled" not in columns:
            connection.execute(
                "ALTER TABLE users ADD COLUMN totp_enabled INTEGER NOT NULL DEFAULT 0"
            )
        if "onboarding_completed" not in columns:
            connection.execute(
                "ALTER TABLE users ADD COLUMN onboarding_completed INTEGER NOT NULL DEFAULT 1"
            )
        if "email_verified" not in columns:
            connection.execute(
                "ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 1"
            )

    @staticmethod
    def _migrate_workspace_memberships(connection: sqlite3.Connection) -> None:
        users = connection.execute(
            """SELECT id, workspace_id, name FROM users
            WHERE id NOT IN (SELECT user_id FROM workspace_memberships WHERE kind = 'prod')"""
        ).fetchall()
        for user in users:
            demo_workspace_id = str(uuid4())
            connection.execute(
                "INSERT INTO workspaces (id, name) VALUES (?, ?)",
                (demo_workspace_id, f"{user['name']}'s Demo workspace"),
            )
            connection.executemany(
                """INSERT INTO workspace_memberships (user_id, workspace_id, kind)
                VALUES (?, ?, ?)""",
                (
                    (user["id"], user["workspace_id"], WorkspaceKind.PROD.value),
                    (user["id"], demo_workspace_id, WorkspaceKind.DEMO.value),
                ),
            )

    @staticmethod
    def _identity(row: sqlite3.Row) -> Identity:
        return Identity(
            user_id=str(row["id"]),
            workspace_id=str(row["workspace_id"]),
            email=str(row["email"]),
            name=str(row["name"]),
            workspace_kind=WorkspaceKind(
                str(row["workspace_kind"]) if "workspace_kind" in row.keys() else "prod"
            ),
            totp_enabled=bool(row["totp_enabled"]) if "totp_enabled" in row.keys() else False,
            onboarding_completed=(
                bool(row["onboarding_completed"]) if "onboarding_completed" in row.keys() else False
            ),
        )
