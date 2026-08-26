import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from pressradar.application.integrations import (
    CRMSyncError,
    NotificationError,
    OpportunityAlert,
    SentOpportunityActivity,
)
from pressradar.infrastructure.hubspot_crm import HubSpotCRMIntegration
from pressradar.infrastructure.twilio_notifications import TwilioNotificationSender


def test_twilio_adapter_uses_authenticated_form_request() -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, json={"sid": "SM123"})

    sender = TwilioNotificationSender(
        account_sid="AC123",
        auth_token="secret-token",
        from_number="+15550000001",
        timeout_seconds=1,
        client=httpx.Client(transport=httpx.MockTransport(respond)),
    )
    sender.send(
        OpportunityAlert(
            opportunity_id="opportunity-1",
            client_company="VertexAI Labs",
            recipient_phone="+15550000002",
            relevance_score=96,
            deadline=_deadline(),
        )
    )

    request = requests[0]
    assert request.method == "POST"
    assert request.url.path.endswith("/Accounts/AC123/Messages.json")
    assert request.headers["authorization"].startswith("Basic ")
    body = request.content.decode()
    assert "From=%2B15550000001" in body
    assert "To=%2B15550000002" in body
    assert "Relevance%3A+96%25" in body


def test_hubspot_adapter_creates_bearer_authenticated_note() -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, json={"id": "note-1"})

    integration = HubSpotCRMIntegration(
        access_token="hubspot-secret",
        timeout_seconds=1,
        client=httpx.Client(transport=httpx.MockTransport(respond)),
    )
    integration.record_sent(
        SentOpportunityActivity(
            opportunity_id="opportunity-1",
            client_name="Nadia Rahman",
            client_company="VertexAI Labs",
            headline="AI governance request",
            sent_at=_deadline(),
        )
    )

    request = requests[0]
    payload = json.loads(request.content)
    assert request.url.path == "/crm/v3/objects/notes"
    assert request.headers["authorization"] == "Bearer hubspot-secret"
    assert payload["properties"]["hs_note_body"].startswith("PressRadar sent opportunity")


@pytest.mark.parametrize(
    ("adapter", "error_type"),
    [
        ("twilio", NotificationError),
        ("hubspot", CRMSyncError),
    ],
)
def test_provider_http_failures_are_translated(adapter: str, error_type: type[Exception]) -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda _request: httpx.Response(503)))
    if adapter == "twilio":
        sender = TwilioNotificationSender(
            account_sid="AC123",
            auth_token="secret",
            from_number="+15550000001",
            timeout_seconds=1,
            client=client,
        )
        with pytest.raises(error_type):
            sender.send(
                OpportunityAlert("opportunity-1", "VertexAI Labs", "+15550000002", 96, _deadline())
            )
    else:
        crm = HubSpotCRMIntegration(access_token="secret", timeout_seconds=1, client=client)
        with pytest.raises(error_type):
            crm.record_sent(
                SentOpportunityActivity(
                    "opportunity-1",
                    "Nadia Rahman",
                    "VertexAI Labs",
                    "AI governance request",
                    _deadline(),
                )
            )


def _deadline() -> datetime:
    return datetime.now(UTC) + timedelta(minutes=42)
