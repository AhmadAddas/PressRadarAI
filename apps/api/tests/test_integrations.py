from pathlib import Path
from typing import cast

import httpx

from pressradar.application.integrations import (
    CRMIntegration,
    CRMSyncError,
    NotificationError,
    NotificationSender,
    OpportunityAlert,
    SentOpportunityActivity,
)
from pressradar.config import Settings
from pressradar.main import create_app


class RecordingNotificationSender:
    def __init__(self, *, fail: bool = False) -> None:
        self.alerts: list[OpportunityAlert] = []
        self._fail = fail

    def send(self, alert: OpportunityAlert) -> None:
        self.alerts.append(alert)
        if self._fail:
            raise NotificationError("provider detail")


class RecordingCRMIntegration:
    def __init__(self, *, fail: bool = False) -> None:
        self.activities: list[SentOpportunityActivity] = []
        self._fail = fail

    def record_sent(self, activity: SentOpportunityActivity) -> None:
        self.activities.append(activity)
        if self._fail:
            raise CRMSyncError("provider detail")


def create_test_client(
    database_path: Path,
    notifications: NotificationSender,
    crm: CRMIntegration,
) -> httpx.AsyncClient:
    app = create_app(
        Settings(database_path=str(database_path), ai_provider="fake"),
        notification_sender=notifications,
        crm_integration=crm,
    )
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def prepare_urgent_opportunity(client: httpx.AsyncClient) -> str:
    assert (
        await client.post(
            "/auth/signup",
            json={
                "email": "integrations@example.com",
                "name": "Owner",
                "password": "secure-passphrase",
            },
        )
    ).status_code == 201
    assert (
        await client.post(
            "/clients",
            json={
                "name": "Nadia Rahman",
                "company": "VertexAI Labs",
                "location": "Dubai",
                "expertise": ["AI governance"],
            },
        )
    ).status_code == 201
    assert (await client.post("/media/ingest")).status_code == 200
    opportunities = (await client.get("/opportunities")).json()
    return cast(str, opportunities[0]["id"])


async def test_integrations_run_at_urgent_and_sent_lifecycle_points(tmp_path: Path) -> None:
    notifications = RecordingNotificationSender()
    crm = RecordingCRMIntegration()
    async with create_test_client(tmp_path / "integrations.db", notifications, crm) as client:
        opportunity_id = await prepare_urgent_opportunity(client)
        assert (
            await client.post(
                "/clients",
                json={
                    "name": "Mariam Al Noor",
                    "company": "GulfFin Advisory",
                    "expertise": ["digital banking"],
                },
            )
        ).status_code == 201
        await client.post("/media/ingest")
        await client.post(f"/opportunities/{opportunity_id}/approve")
        sent = await client.post(f"/opportunities/{opportunity_id}/send")
        replay = await client.post(f"/opportunities/{opportunity_id}/send")

    assert sent.status_code == 200
    assert replay.status_code == 200
    assert len(notifications.alerts) == 1
    assert notifications.alerts[0].relevance_score == 91
    assert len(crm.activities) == 1
    assert crm.activities[0].client_company == "VertexAI Labs"


async def test_integration_failures_do_not_invalidate_core_workflow(tmp_path: Path) -> None:
    notifications = RecordingNotificationSender(fail=True)
    crm = RecordingCRMIntegration(fail=True)
    async with create_test_client(tmp_path / "failures.db", notifications, crm) as client:
        opportunity_id = await prepare_urgent_opportunity(client)
        ready = (await client.get("/opportunities")).json()[0]
        await client.post(f"/opportunities/{opportunity_id}/approve")
        sent = await client.post(f"/opportunities/{opportunity_id}/send")
        audit = await client.get(f"/opportunities/{opportunity_id}/audit")

    assert ready["status"] == "ready"
    assert sent.json()["status"] == "sent"
    failures = [event for event in audit.json() if event["action"] == "integration_sync_failed"]
    assert [event["detail"] for event in failures] == [
        "Notification delivery failed",
        "CRM synchronization failed",
    ]
