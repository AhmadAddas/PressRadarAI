from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class MediaSourceType(StrEnum):
    NEWS = "news"
    JOURNALIST_REQUEST = "journalist_request"
    RSS = "rss"
    SOCIAL = "social"


@dataclass(frozen=True)
class IncomingMediaItem:
    source: str
    source_type: MediaSourceType
    headline: str
    body: str
    published_at: datetime
    author: str | None = None
    journalist: str | None = None
    url: str | None = None
    deadline: datetime | None = None
    topics: tuple[str, ...] = ()
    external_id: str | None = None
    display_headline: str | None = None


@dataclass(frozen=True)
class MediaItem:
    id: str
    source: str
    source_type: MediaSourceType
    headline: str
    body: str
    published_at: datetime
    ingested_at: datetime
    author: str | None
    journalist: str | None
    url: str | None
    deadline: datetime | None
    topics: tuple[str, ...]
    external_id: str | None
    display_headline: str | None = None


@dataclass(frozen=True)
class IngestionResult:
    created: int
    restored: int
    duplicates: int
