import httpx

from pressradar.application.email import EmailDeliveryError, EmailMessage


class NodemailerEmailSender:
    def __init__(self, *, base_url: str, internal_token: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._internal_token = internal_token
        self._timeout = timeout_seconds

    def send(self, message: EmailMessage) -> str:
        try:
            response = httpx.post(
                f"{self._base_url}/send",
                headers={"Authorization": f"Bearer {self._internal_token}"},
                json={
                    "to": message.recipient,
                    "subject": message.subject,
                    "text": message.text,
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            message_id = response.json().get("message_id")
            if not isinstance(message_id, str) or not message_id:
                raise EmailDeliveryError
            return message_id
        except (httpx.HTTPError, ValueError, EmailDeliveryError) as error:
            raise EmailDeliveryError from error
