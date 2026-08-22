from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ProductEventName(StrEnum):
    OPPORTUNITY_DETECTED = "opportunity_detected"
    ANALYSIS_COMPLETED = "analysis_completed"
    PITCH_REVIEWED = "pitch_reviewed"
    PITCH_APPROVED = "pitch_approved"
    PITCH_SENT = "pitch_sent"
    OPPORTUNITY_DISMISSED = "opportunity_dismissed"


@dataclass(frozen=True)
class ProductEvent:
    id: str
    workspace_id: str
    name: ProductEventName
    occurred_at: datetime
    opportunity_id: str
    client_id: str
    client_name: str
    source: str
    relevance_score: int | None
    detected_at: datetime


@dataclass(frozen=True)
class SourcePerformance:
    source: str
    opportunities: int
    sent: int


@dataclass(frozen=True)
class ClientVolume:
    client_id: str
    client_name: str
    opportunities: int


@dataclass(frozen=True)
class AnalyticsSummary:
    opportunities_detected: int
    average_relevance_score: float | None
    average_seconds_to_review: float | None
    average_seconds_to_send: float | None
    approval_rate: float
    pitch_send_rate: float
    dismissal_rate: float
    sources: tuple[SourcePerformance, ...]
    clients: tuple[ClientVolume, ...]
