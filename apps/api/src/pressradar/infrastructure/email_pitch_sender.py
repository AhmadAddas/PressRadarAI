from pressradar.application.delivery import PitchSendError
from pressradar.application.email import EmailDeliveryError, EmailMessage, EmailSender
from pressradar.domain.delivery import DeliveryReceipt, DeliveryRequest


class EmailPitchSender:
    def __init__(self, email_sender: EmailSender) -> None:
        self._email_sender = email_sender

    def send(self, request: DeliveryRequest) -> DeliveryReceipt:
        try:
            reference = self._email_sender.send(
                EmailMessage(
                    recipient=request.recipient,
                    subject="PressRadar pitch",
                    text=request.content,
                    message_id=request.idempotency_key,
                )
            )
        except EmailDeliveryError as error:
            raise PitchSendError from error
        return DeliveryReceipt(provider="email", reference=reference)
