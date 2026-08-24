import ipaddress
import socket
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from io import StringIO
from typing import cast
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx

from pressradar.application.media import (
    InvalidMediaItemError,
    MediaIngestionService,
    MediaRepository,
)
from pressradar.application.media_sources import MediaSourceRepository
from pressradar.domain.media import IncomingMediaItem, IngestionResult, MediaSourceType
from pressradar.domain.media_sources import MediaSource, MediaSourceKind


class MediaSourceConfigurationError(Exception):
    """Raised when a configured production source cannot be used safely."""


MAX_ITEMS_PER_SOURCE = 25
MAX_ITEMS_PER_INGESTION = 100


class ConfiguredMediaIngestionService:
    def __init__(
        self,
        sources: MediaSourceRepository,
        media: MediaRepository,
        *,
        newsapi_api_key: str,
        timeout_seconds: float,
    ) -> None:
        self._sources = sources
        self._media = media
        self._newsapi_api_key = newsapi_api_key
        self._timeout_seconds = timeout_seconds

    def ingest(self, *, workspace_id: str) -> IngestionResult:
        items: list[IncomingMediaItem] = []
        for source in self._sources.list(workspace_id=workspace_id, kind=None):
            remaining = MAX_ITEMS_PER_INGESTION - len(items)
            if remaining <= 0:
                break
            source_limit = min(MAX_ITEMS_PER_SOURCE, remaining)
            if source.kind is MediaSourceKind.RSS:
                items.extend(self._fetch_rss(source, limit=source_limit))
            elif source.provider == "newsapi":
                items.extend(self._fetch_newsapi(source, limit=source_limit))
        normalized = tuple(MediaIngestionService.normalize(item) for item in items)
        return self._media.ingest(workspace_id=workspace_id, items=normalized)

    def _fetch_rss(self, source: MediaSource, *, limit: int) -> tuple[IncomingMediaItem, ...]:
        if source.url is None:
            raise MediaSourceConfigurationError(f"{source.name} has no RSS URL")
        _require_public_https(source.url)
        try:
            response = httpx.get(source.url, timeout=self._timeout_seconds, follow_redirects=False)
            response.raise_for_status()
            root = ElementTree.fromstring(response.content)
        except (httpx.HTTPError, ElementTree.ParseError) as error:
            raise MediaSourceConfigurationError(f"Unable to fetch {source.name}") from error
        return tuple(_rss_item(source.name, item) for item in root.findall(".//item")[:limit])

    def _fetch_newsapi(self, source: MediaSource, *, limit: int) -> tuple[IncomingMediaItem, ...]:
        if not self._newsapi_api_key:
            raise MediaSourceConfigurationError("NEWSAPI_API_KEY is required for NewsAPI")
        articles = self._request_newsapi(
            "https://newsapi.org/v2/top-headlines",
            {"country": "ae", "pageSize": limit},
        )
        if not articles:
            articles = self._request_newsapi(
                "https://newsapi.org/v2/everything",
                {
                    "q": '"United Arab Emirates" OR UAE OR Dubai OR "Abu Dhabi"',
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": limit,
                },
            )
        return tuple(_newsapi_item(source.name, article) for article in articles[:limit])

    def _request_newsapi(self, url: str, params: dict[str, str | int]) -> list[object]:
        try:
            response = httpx.get(
                url,
                params=params,
                headers={"X-Api-Key": self._newsapi_api_key},
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            if (
                not isinstance(payload, dict)
                or payload.get("status") != "ok"
                or not isinstance(payload.get("articles"), list)
            ):
                raise ValueError("NewsAPI returned an invalid response")
        except (httpx.HTTPError, ValueError) as error:
            raise MediaSourceConfigurationError("Unable to fetch NewsAPI") from error
        return cast(list[object], payload["articles"])


def _rss_item(source: str, item: ElementTree.Element) -> IncomingMediaItem:
    headline = _xml_text(item, "title")
    link = _xml_text(item, "link") or None
    published = _parse_time(_xml_text(item, "pubDate"))
    return IncomingMediaItem(
        source=source,
        source_type=MediaSourceType.RSS,
        headline=headline,
        body=_plain_text(_xml_text(item, "description")) or headline,
        url=link,
        published_at=published,
        external_id=_xml_text(item, "guid") or link,
    )


def _newsapi_item(source: str, article: object) -> IncomingMediaItem:
    if not isinstance(article, dict):
        raise InvalidMediaItemError("NewsAPI returned an invalid article")
    published = article.get("publishedAt")
    try:
        published_at = datetime.fromisoformat(str(published).replace("Z", "+00:00"))
    except ValueError as error:
        raise InvalidMediaItemError("NewsAPI returned an invalid timestamp") from error
    return IncomingMediaItem(
        source=str(article.get("source", {}).get("name") or source),
        source_type=MediaSourceType.NEWS,
        headline=str(article.get("title") or ""),
        body=str(article.get("description") or article.get("content") or ""),
        author=None if article.get("author") is None else str(article["author"]),
        url=None if article.get("url") is None else str(article["url"]),
        published_at=published_at,
        external_id=None if article.get("url") is None else str(article["url"]),
    )


def _require_public_https(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise MediaSourceConfigurationError("RSS URL must be public HTTPS")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443)
    except socket.gaierror as error:
        raise MediaSourceConfigurationError("RSS hostname could not be resolved") from error
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise MediaSourceConfigurationError("RSS URL must resolve to a public network")


def _xml_text(item: ElementTree.Element, name: str) -> str:
    element = item.find(name)
    return "" if element is None or element.text is None else element.text.strip()


def _parse_time(value: str) -> datetime:
    if not value:
        return datetime.now(UTC)
    try:
        result = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise InvalidMediaItemError("RSS returned an invalid timestamp") from error
    return result.replace(tzinfo=UTC) if result.tzinfo is None else result.astimezone(UTC)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.output = StringIO()

    def handle_data(self, data: str) -> None:
        self.output.write(data)


def _plain_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    return " ".join(parser.output.getvalue().split())
