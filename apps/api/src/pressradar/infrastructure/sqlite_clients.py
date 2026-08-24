import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from pressradar.domain.clients import Client, ClientDetails


class SQLiteClientRepository:
    def __init__(self, database_path: str) -> None:
        self._database_path = database_path

    def initialize(self) -> None:
        Path(self._database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS clients (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    company TEXT NOT NULL,
                    website TEXT,
                    industry TEXT,
                    description TEXT,
                    location TEXT,
                    expertise TEXT NOT NULL,
                    spokesperson_name TEXT,
                    spokesperson_title TEXT,
                    keywords TEXT NOT NULL,
                    excluded_keywords TEXT NOT NULL,
                    preferred_topics TEXT NOT NULL,
                    tone TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_clients_workspace ON clients(workspace_id);
                CREATE TABLE IF NOT EXISTS monitoring_rules (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                    query TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_rules_client ON monitoring_rules(client_id);
                """
            )
            self._add_deleted_column(connection)
            self._add_contact_columns(connection)

    def create(self, *, workspace_id: str, details: ClientDetails) -> Client:
        client_id = str(uuid4())
        with self._connect() as connection:
            self._insert_client(connection, client_id, workspace_id, details)
            self._replace_rules(connection, client_id, details.monitoring_rules)
        client = self.get(workspace_id=workspace_id, client_id=client_id)
        if client is None:
            raise RuntimeError("Created client could not be loaded")
        return client

    def list(self, *, workspace_id: str) -> list[Client]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM clients WHERE workspace_id = ? AND deleted_at IS NULL
                ORDER BY name COLLATE NOCASE, id""",
                (workspace_id,),
            ).fetchall()
            return [self._client(connection, row) for row in rows]

    def get(self, *, workspace_id: str, client_id: str) -> Client | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM clients
                WHERE id = ? AND workspace_id = ? AND deleted_at IS NULL""",
                (client_id, workspace_id),
            ).fetchone()
            return None if row is None else self._client(connection, row)

    def update(self, *, workspace_id: str, client_id: str, details: ClientDetails) -> Client | None:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE clients SET name = ?, company = ?, website = ?, industry = ?,
                description = ?, location = ?, expertise = ?, spokesperson_name = ?,
                spokesperson_title = ?, keywords = ?, excluded_keywords = ?,
                preferred_topics = ?, tone = ?, email = ?, phone = ?
                WHERE id = ? AND workspace_id = ? AND deleted_at IS NULL""",
                (*self._detail_values(details), client_id, workspace_id),
            )
            if cursor.rowcount == 0:
                return None
            self._replace_rules(connection, client_id, details.monitoring_rules)
        return self.get(workspace_id=workspace_id, client_id=client_id)

    def delete(self, *, workspace_id: str, client_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE clients SET deleted_at = CURRENT_TIMESTAMP
                WHERE id = ? AND workspace_id = ? AND deleted_at IS NULL""",
                (client_id, workspace_id),
            )
        return cursor.rowcount > 0

    @staticmethod
    def _add_deleted_column(connection: sqlite3.Connection) -> None:
        columns = {str(row["name"]) for row in connection.execute("PRAGMA table_info(clients)")}
        if "deleted_at" not in columns:
            connection.execute("ALTER TABLE clients ADD COLUMN deleted_at TEXT")

    @staticmethod
    def _add_contact_columns(connection: sqlite3.Connection) -> None:
        columns = {str(row["name"]) for row in connection.execute("PRAGMA table_info(clients)")}
        if "email" not in columns:
            connection.execute("ALTER TABLE clients ADD COLUMN email TEXT")
        if "phone" not in columns:
            connection.execute("ALTER TABLE clients ADD COLUMN phone TEXT")

    def _insert_client(
        self,
        connection: sqlite3.Connection,
        client_id: str,
        workspace_id: str,
        details: ClientDetails,
    ) -> None:
        connection.execute(
            """INSERT INTO clients (
                id, workspace_id, name, company, website, industry, description, location,
                expertise, spokesperson_name, spokesperson_title, keywords,
                excluded_keywords, preferred_topics, tone, email, phone
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (client_id, workspace_id, *self._detail_values(details)),
        )

    @staticmethod
    def _detail_values(details: ClientDetails) -> tuple[object, ...]:
        return (
            details.name,
            details.company,
            details.website,
            details.industry,
            details.description,
            details.location,
            json.dumps(details.expertise),
            details.spokesperson_name,
            details.spokesperson_title,
            json.dumps(details.keywords),
            json.dumps(details.excluded_keywords),
            json.dumps(details.preferred_topics),
            details.tone,
            details.email,
            details.phone,
        )

    @staticmethod
    def _replace_rules(
        connection: sqlite3.Connection, client_id: str, monitoring_rules: tuple[str, ...]
    ) -> None:
        connection.execute("DELETE FROM monitoring_rules WHERE client_id = ?", (client_id,))
        connection.executemany(
            "INSERT INTO monitoring_rules (id, client_id, query) VALUES (?, ?, ?)",
            [(str(uuid4()), client_id, query) for query in monitoring_rules],
        )

    @staticmethod
    def _client(connection: sqlite3.Connection, row: sqlite3.Row) -> Client:
        rules = connection.execute(
            "SELECT query FROM monitoring_rules WHERE client_id = ? ORDER BY rowid",
            (row["id"],),
        ).fetchall()
        return Client(
            id=str(row["id"]),
            workspace_id=str(row["workspace_id"]),
            name=str(row["name"]),
            company=str(row["company"]),
            website=None if row["website"] is None else str(row["website"]),
            industry=None if row["industry"] is None else str(row["industry"]),
            description=None if row["description"] is None else str(row["description"]),
            location=None if row["location"] is None else str(row["location"]),
            expertise=tuple(json.loads(row["expertise"])),
            spokesperson_name=(
                None if row["spokesperson_name"] is None else str(row["spokesperson_name"])
            ),
            spokesperson_title=(
                None if row["spokesperson_title"] is None else str(row["spokesperson_title"])
            ),
            keywords=tuple(json.loads(row["keywords"])),
            excluded_keywords=tuple(json.loads(row["excluded_keywords"])),
            preferred_topics=tuple(json.loads(row["preferred_topics"])),
            tone=None if row["tone"] is None else str(row["tone"]),
            monitoring_rules=tuple(str(rule["query"]) for rule in rules),
            email=None if row["email"] is None else str(row["email"]),
            phone=None if row["phone"] is None else str(row["phone"]),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
