from typing import Protocol

from pressradar.domain.delivery import DeliveryReceipt, DeliveryRequest


class PitchSendError(Exception):
    """Raised when a pitch sender cannot complete simulated or real delivery."""


class PitchSender(Protocol):
    def send(self, request: DeliveryRequest) -> DeliveryReceipt: ...
