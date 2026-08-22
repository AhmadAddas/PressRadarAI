from typing import Protocol

from pressradar.domain.media_sources import MediaSource, MediaSourceDetails, MediaSourceKind


class MediaSourceNotFoundError(Exception):
    """Raised when a source is not visible in the current workspace."""


class DuplicateMediaSourceError(Exception):
    """Raised when a workspace already has a source with the same name."""


class MediaSourceRepository(Protocol):
    def create(self, *, workspace_id: str, details: MediaSourceDetails) -> MediaSource: ...

    def list(self, *, workspace_id: str, kind: MediaSourceKind | None) -> list[MediaSource]: ...

    def delete(self, *, workspace_id: str, source_id: str) -> bool: ...


class MediaSourceService:
    def __init__(self, repository: MediaSourceRepository) -> None:
        self._repository = repository

    def create(self, *, workspace_id: str, details: MediaSourceDetails) -> MediaSource:
        return self._repository.create(workspace_id=workspace_id, details=details)

    def list(self, *, workspace_id: str, kind: MediaSourceKind | None = None) -> list[MediaSource]:
        return self._repository.list(workspace_id=workspace_id, kind=kind)

    def delete(self, *, workspace_id: str, source_id: str) -> None:
        if not self._repository.delete(workspace_id=workspace_id, source_id=source_id):
            raise MediaSourceNotFoundError


UAE_SOURCE_SUGGESTIONS = (
    {
        "name": "UAE headlines via NewsAPI",
        "kind": MediaSourceKind.API,
        "provider": "newsapi",
        "url": None,
    },
    {
        "name": "Emirates Media Centre",
        "kind": MediaSourceKind.RSS,
        "provider": None,
        "url": "https://www.emirates.com/media-centre/feed/en-us",
    },
)
