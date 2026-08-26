from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class NotificationError(Exception):
    """Raised when an optional notification provider cannot deliver an alert."""


class CRMSyncError(Exception):
    """Raised when an optional CRM provider cannot record activity."""


@dataclass(frozen=True)
class OpportunityAlert:
    opportunity_id: str
    client_company: str
    recipient_phone: str
    relevance_score: int
    deadline: datetime


@dataclass(frozen=True)
class SentOpportunityActivity:
    opportunity_id: str
    client_name: str
    client_company: str
    headline: str
    sent_at: datetime


class NotificationSender(Protocol):
    def send(self, alert: OpportunityAlert) -> None: ...


class CRMIntegration(Protocol):
    def record_sent(self, activity: SentOpportunityActivity) -> None: ...
