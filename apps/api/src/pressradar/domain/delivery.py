from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DeliveryRequest:
    opportunity_id: str
    recipient: str
    content: str
    idempotency_key: str | None = None


@dataclass(frozen=True)
class DeliveryReceipt:
    provider: str
    reference: str


@dataclass(frozen=True)
class Delivery:
    provider: str
    reference: str
    sent_at: datetime
