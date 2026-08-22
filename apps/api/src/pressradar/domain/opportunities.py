from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class OpportunityStatus(StrEnum):
    NEW = "new"
    ANALYZING = "analyzing"
    READY = "ready"
    APPROVED = "approved"
    SENT = "sent"
    DISMISSED = "dismissed"
    FAILED = "failed"


ALLOWED_TRANSITIONS: dict[OpportunityStatus, frozenset[OpportunityStatus]] = {
    OpportunityStatus.NEW: frozenset({OpportunityStatus.ANALYZING, OpportunityStatus.DISMISSED}),
    OpportunityStatus.ANALYZING: frozenset({OpportunityStatus.READY, OpportunityStatus.FAILED}),
    OpportunityStatus.READY: frozenset({OpportunityStatus.APPROVED, OpportunityStatus.DISMISSED}),
    OpportunityStatus.APPROVED: frozenset({OpportunityStatus.SENT}),
    OpportunityStatus.SENT: frozenset(),
    OpportunityStatus.DISMISSED: frozenset(),
    OpportunityStatus.FAILED: frozenset(),
}


@dataclass(frozen=True)
class Opportunity:
    id: str
    workspace_id: str
    client_id: str
    client_name: str
    client_company: str
    media_item_id: str
    source: str
    headline: str
    journalist: str | None
    published_at: datetime
    deadline: datetime | None
    matched_topics: tuple[str, ...]
    status: OpportunityStatus
    detected_at: datetime


@dataclass(frozen=True)
class OpportunityMatch:
    workspace_id: str
    client_id: str
    media_item_id: str
    matched_topics: tuple[str, ...]
