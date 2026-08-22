from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from pressradar.domain.media import IncomingMediaItem, MediaSourceType


class SimulatedMediaProvider:
    def __init__(self, now: Callable[[], datetime] | None = None) -> None:
        self._now = now or (lambda: datetime.now(UTC))

    def fetch_items(self) -> tuple[IncomingMediaItem, ...]:
        now = self._now().astimezone(UTC)
        return (
            IncomingMediaItem(
                source="Gulf Business Desk",
                source_type=MediaSourceType.JOURNALIST_REQUEST,
                journalist="Layla Hassan",
                headline="Dubai AI founders wanted for governance commentary",
                body=(
                    "Looking for Dubai-based AI founders to comment on how new UAE AI "
                    "governance requirements could affect early-stage startups."
                ),
                published_at=now,
                deadline=now + timedelta(minutes=60),
                topics=("AI governance", "Dubai startups", "UAE technology"),
                external_id="demo-request-ai-governance-001",
            ),
            IncomingMediaItem(
                source="Emirates Finance Wire",
                source_type=MediaSourceType.NEWS,
                author="Omar Saleh",
                headline="UAE digital banks prepare for new compliance phase",
                body="Regional digital banks are reviewing compliance and approval processes.",
                url="https://example.com/uae-digital-banking-compliance",
                published_at=now - timedelta(minutes=30),
                topics=("fintech", "digital banking", "regulation"),
                external_id="demo-news-fintech-001",
            ),
            IncomingMediaItem(
                source="Dubai Startup Feed",
                source_type=MediaSourceType.RSS,
                headline="Dubai startup funding activity increases this quarter",
                body="Investors report renewed interest in enterprise technology startups.",
                url="https://example.com/dubai-startup-funding",
                published_at=now - timedelta(hours=2),
                topics=("startup funding", "Dubai", "enterprise technology"),
                external_id="demo-rss-startups-001",
            ),
        )
