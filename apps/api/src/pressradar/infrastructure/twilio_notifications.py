from datetime import UTC, datetime

import httpx

from pressradar.application.integrations import NotificationError, OpportunityAlert


class TwilioNotificationSender:
    def __init__(
        self,
        *,
        account_sid: str,
        auth_token: str,
        from_number: str,
        to_number: str,
        timeout_seconds: float,
        client: httpx.Client | None = None,
    ) -> None:
        self._url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        self._auth = (account_sid, auth_token)
        self._from_number = from_number
        self._to_number = to_number
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def send(self, alert: OpportunityAlert) -> None:
        remaining_minutes = max(
            0,
            round((alert.deadline - datetime.now(UTC)).total_seconds() / 60),
        )
        try:
            response = self._client.post(
                self._url,
                auth=self._auth,
                data={
                    "From": self._from_number,
                    "To": self._to_number,
                    "Body": (
                        "High-priority opportunity detected. "
                        f"Client: {alert.client_company}. "
                        f"Relevance: {alert.relevance_score}%. "
                        f"Deadline: {remaining_minutes} minutes."
                    ),
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise NotificationError("Twilio notification failed") from error
