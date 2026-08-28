from dataclasses import dataclass
from typing import Protocol


class EmailDeliveryError(Exception):
    """Raised when transactional email cannot be delivered."""


@dataclass(frozen=True)
class EmailMessage:
    recipient: str
    subject: str
    text: str
    message_id: str | None = None


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> str: ...


class FakeEmailSender:
    """Deterministic adapter used by tests and unconfigured local environments."""

    def send(self, message: EmailMessage) -> str:
        return f"fake:{message.recipient}"
