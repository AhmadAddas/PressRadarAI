import hashlib
from dataclasses import replace
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import urlparse

from pressradar.domain.media import IncomingMediaItem, IngestionResult, MediaItem


class MediaProvider(Protocol):
    def fetch_items(self) -> tuple[IncomingMediaItem, ...]: ...


class MediaRepository(Protocol):
    def ingest(
        self, *, workspace_id: str, items: tuple[IncomingMediaItem, ...]
    ) -> IngestionResult: ...

    def list(self, *, workspace_id: str, limit: int) -> list[MediaItem]: ...

    def get(self, *, workspace_id: str, media_item_id: str) -> MediaItem | None: ...

    def delete(self, *, workspace_id: str, media_item_id: str) -> bool: ...

    def update_deadline(
        self, *, workspace_id: str, media_item_id: str, deadline: datetime | None
    ) -> MediaItem | None: ...

    def clear(self, *, workspace_id: str) -> None: ...


class InvalidMediaItemError(Exception):
    """Raised when a provider returns unsafe or incomplete media data."""


class MediaItemNotFoundError(Exception):
    """Raised when a media item is not visible in the current workspace."""


class MediaIngestionService:
    def __init__(self, provider: MediaProvider, repository: MediaRepository) -> None:
        self._provider = provider
        self._repository = repository

    def ingest(self, *, workspace_id: str) -> IngestionResult:
        return self._repository.ingest(
            workspace_id=workspace_id,
            items=tuple(self.normalize(item) for item in self._provider.fetch_items()),
        )

    def list(self, *, workspace_id: str, limit: int = 100) -> list[MediaItem]:
        return self._repository.list(workspace_id=workspace_id, limit=limit)

    def delete(self, *, workspace_id: str, media_item_id: str) -> None:
        if not self._repository.delete(workspace_id=workspace_id, media_item_id=media_item_id):
            raise MediaItemNotFoundError

    def update_deadline(
        self, *, workspace_id: str, media_item_id: str, deadline: datetime | None
    ) -> MediaItem:
        normalized = None if deadline is None else _utc(deadline)
        item = self._repository.update_deadline(
            workspace_id=workspace_id,
            media_item_id=media_item_id,
            deadline=normalized,
        )
        if item is None:
            raise MediaItemNotFoundError
        return item

    def clear(self, *, workspace_id: str) -> None:
        self._repository.clear(workspace_id=workspace_id)

    @staticmethod
    def dedupe_key(item: IncomingMediaItem) -> str:
        if item.external_id:
            identity = f"external:{item.source.casefold()}:{item.external_id.casefold()}"
        else:
            identity = "fallback:" + "|".join(
                (
                    item.source.casefold(),
                    item.headline.casefold(),
                    item.url or "",
                    item.published_at.isoformat(),
                )
            )
        return hashlib.sha256(identity.encode()).hexdigest()

    @staticmethod
    def normalize(item: IncomingMediaItem) -> IncomingMediaItem:
        source = item.source.strip()
        headline = item.headline.strip()
        body = item.body.strip()
        if not source or not headline or not body:
            raise InvalidMediaItemError("Media source, headline, and body are required")
        if len(source) > 100 or len(headline) > 500 or len(body) > 20_000:
            raise InvalidMediaItemError("Media item exceeds supported length")
        if item.url and (
            len(item.url) > 2_000 or urlparse(item.url).scheme not in {"http", "https"}
        ):
            raise InvalidMediaItemError("Media URL must use HTTP or HTTPS")
        author = _optional(item.author)
        journalist = _optional(item.journalist)
        external_id = _optional(item.external_id)
        if any(
            value and len(value) > limit
            for value, limit in ((author, 200), (journalist, 200), (external_id, 500))
        ):
            raise InvalidMediaItemError("Media metadata exceeds supported length")
        published_at = _utc(item.published_at)
        deadline = None if item.deadline is None else _utc(item.deadline)
        topics = tuple(dict.fromkeys(topic.strip() for topic in item.topics if topic.strip()))
        if len(topics) > 50 or any(len(topic) > 100 for topic in topics):
            raise InvalidMediaItemError("Media topics exceed supported limits")
        return replace(
            item,
            source=source,
            headline=headline,
            body=body,
            author=author,
            journalist=journalist,
            external_id=external_id,
            published_at=published_at,
            deadline=deadline,
            topics=topics,
        )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise InvalidMediaItemError("Media timestamps must include a timezone")
    return value.astimezone(UTC)


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
