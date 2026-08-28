import sqlite3
from types import TracebackType
from typing import Literal


class ClosingConnection(sqlite3.Connection):
    """Commit or roll back a transaction, then release its database handle."""

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect(database_path: str) -> sqlite3.Connection:
    return sqlite3.connect(database_path, timeout=5, factory=ClosingConnection)
