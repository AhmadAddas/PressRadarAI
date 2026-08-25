from pressradar.application.delivery import PitchSendError
from pressradar.application.email import EmailDeliveryError, EmailMessage
from pressradar.domain.delivery import DeliveryRequest
from pressradar.infrastructure.email_pitch_sender import EmailPitchSender


class RecordingSender:
    def __init__(self, fails: bool = False) -> None:
        self.fails = fails
        self.message: EmailMessage | None = None

    def send(self, message: EmailMessage) -> str:
        self.message = message
        if self.fails:
            raise EmailDeliveryError
        return "outlook-message-1"


def test_email_pitch_sender_delivers_the_approved_content() -> None:
    email = RecordingSender()
    receipt = EmailPitchSender(email).send(
        DeliveryRequest(
            opportunity_id="opportunity-1",
            recipient="client@example.com",
            content="Approved pitch content.",
        )
    )

    assert email.message == EmailMessage(
        recipient="client@example.com",
        subject="PressRadar pitch",
        text="Approved pitch content.",
    )
    assert receipt.provider == "email"
    assert receipt.reference == "outlook-message-1"


def test_email_pitch_sender_maps_provider_failures() -> None:
    try:
        EmailPitchSender(RecordingSender(fails=True)).send(
            DeliveryRequest("opportunity-1", "client@example.com", "Pitch")
        )
    except PitchSendError:
        pass
    else:
        raise AssertionError("Expected PitchSendError")
