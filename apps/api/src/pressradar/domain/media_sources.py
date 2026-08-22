from dataclasses import dataclass
from enum import StrEnum


class MediaSourceKind(StrEnum):
    RSS = "rss"
    API = "api"


@dataclass(frozen=True)
class MediaSource:
    id: str
    workspace_id: str
    name: str
    kind: MediaSourceKind
    url: str | None
    provider: str | None


@dataclass(frozen=True)
class MediaSourceDetails:
    name: str
    kind: MediaSourceKind
    url: str | None
    provider: str | None
