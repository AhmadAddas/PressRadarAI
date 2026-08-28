import asyncio
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import httpx

from pressradar.application.delivery import PitchSender, PitchSendError
from pressradar.config import Settings
from pressradar.domain.delivery import DeliveryReceipt, DeliveryRequest
from pressradar.main import create_app


class CountingSender:
    def __init__(self) -> None:
        self.calls = 0
        self.idempotency_keys: list[str | None] = []

    def send(self, request: DeliveryRequest) -> DeliveryReceipt:
        self.calls += 1
        self.idempotency_keys.append(request.idempotency_key)
        return DeliveryReceipt(
            provider="counting-simulated",
            reference=f"delivery:{request.opportunity_id}",
        )


class FlakySender:
    def __init__(self) -> None:
        self.calls = 0

    def send(self, request: DeliveryRequest) -> DeliveryReceipt:
        self.calls += 1
        if self.calls == 1:
            raise PitchSendError("simulated provider detail must not leak")
        return DeliveryReceipt(
            provider="flaky-simulated",
            reference=f"retry:{request.opportunity_id}",
        )


class BlockingSender:
    def __init__(self) -> None:
        self.calls = 0
        self.started = threading.Event()
        self.release = threading.Event()

    def send(self, request: DeliveryRequest) -> DeliveryReceipt:
        self.calls += 1
        self.started.set()
        if not self.release.wait(timeout=5):
            raise PitchSendError("test delivery timed out")
        return DeliveryReceipt(provider="blocking-simulated", reference=request.opportunity_id)


def create_test_client(database_path: Path, sender: PitchSender) -> httpx.AsyncClient:
    app = create_app(
        Settings(database_path=str(database_path), ai_provider="fake"),
        pitch_sender=sender,
    )
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def prepare_opportunity(client: httpx.AsyncClient, email: str = "sender@example.com") -> str:
    signup = await client.post(
        "/auth/signup",
        json={"email": email, "name": "Owner", "password": "secure-passphrase"},
    )
    assert signup.status_code == 201
    assert (
        await client.post("/auth/workspace", json={"workspace_kind": "demo"})
    ).status_code == 200
    created = await client.post(
        "/clients",
        json={
            "name": "Nadia Rahman",
            "company": "VertexAI Labs",
            "location": "Dubai",
            "expertise": ["AI governance"],
        },
    )
    assert created.status_code == 201
    assert (await client.post("/media/ingest")).status_code == 200
    payload = (await client.get("/opportunities")).json()
    assert isinstance(payload, list)
    assert isinstance(payload[0], dict)
    return cast(str, payload[0]["id"])


async def test_pitch_requires_explicit_approval_and_sends_only_once(tmp_path: Path) -> None:
    sender = CountingSender()
    async with create_test_client(tmp_path / "send.db", sender) as client:
        opportunity_id = await prepare_opportunity(client)
        bypass = await client.post(f"/opportunities/{opportunity_id}/send")
        bypass_status = await client.patch(
            f"/opportunities/{opportunity_id}/status", json={"status": "approved"}
        )
        approved = await client.post(f"/opportunities/{opportunity_id}/approve")
        sent = await client.post(f"/opportunities/{opportunity_id}/send")
        replay = await client.post(f"/opportunities/{opportunity_id}/send")

    assert bypass.status_code == 409
    assert bypass_status.status_code == 409
    assert sender.calls == 1
    assert approved.json()["status"] == "approved"
    assert sent.json()["status"] == "sent"
    assert sent.json()["delivery"]["provider"] == "counting-simulated"
    assert replay.json()["delivery"] == sent.json()["delivery"]


async def test_failed_send_preserves_approval_and_can_be_retried(tmp_path: Path) -> None:
    sender = FlakySender()
    async with create_test_client(tmp_path / "retry.db", sender) as client:
        opportunity_id = await prepare_opportunity(client)
        await client.post(f"/opportunities/{opportunity_id}/approve")
        failed = await client.post(f"/opportunities/{opportunity_id}/send")
        after_failure = (await client.get("/opportunities")).json()[0]
        retried = await client.post(f"/opportunities/{opportunity_id}/send")

    assert failed.status_code == 502
    assert failed.json()["detail"] == "Pitch delivery failed and can be retried"
    assert after_failure["status"] == "approved"
    assert after_failure["send_error"] == (
        "Simulated delivery failed. The approved pitch can be retried."
    )
    assert "provider detail" not in after_failure["send_error"]
    assert retried.status_code == 200
    assert retried.json()["status"] == "sent"
    assert sender.calls == 2


async def test_stale_send_claim_is_recovered_with_stable_idempotency_key(
    tmp_path: Path,
) -> None:
    database = tmp_path / "recover-send.db"
    sender = CountingSender()
    async with create_test_client(database, sender) as client:
        opportunity_id = await prepare_opportunity(client)
        await client.post(f"/opportunities/{opportunity_id}/approve")
        with sqlite3.connect(database) as connection:
            connection.execute(
                """UPDATE opportunities SET status = ?, send_claimed_at = ? WHERE id = ?""",
                (
                    "sending",
                    (datetime.now(UTC) - timedelta(minutes=6)).isoformat(),
                    opportunity_id,
                ),
            )
        recovered = await client.post(f"/opportunities/{opportunity_id}/send")

    assert recovered.status_code == 200
    assert recovered.json()["status"] == "sent"
    assert sender.idempotency_keys == [f"pressradar-{opportunity_id}@delivery.local"]


async def test_concurrent_send_requests_create_one_delivery(tmp_path: Path) -> None:
    sender = BlockingSender()
    async with create_test_client(tmp_path / "concurrent-send.db", sender) as client:
        opportunity_id = await prepare_opportunity(client, "concurrent-send@example.com")
        await client.post(f"/opportunities/{opportunity_id}/approve")
        first = asyncio.create_task(client.post(f"/opportunities/{opportunity_id}/send"))
        assert await asyncio.to_thread(sender.started.wait, 2)
        second = await client.post(f"/opportunities/{opportunity_id}/send")
        sender.release.set()
        first_response = await first

    assert sorted([first_response.status_code, second.status_code]) == [200, 409]
    assert sender.calls == 1


async def test_audit_history_records_workflow_and_is_workspace_scoped(tmp_path: Path) -> None:
    database = tmp_path / "audit.db"
    sender = CountingSender()
    async with create_test_client(database, sender) as owner:
        opportunity_id = await prepare_opportunity(owner)
        await owner.post(f"/opportunities/{opportunity_id}/approve")
        await owner.post(f"/opportunities/{opportunity_id}/send")
        audit = await owner.get(f"/opportunities/{opportunity_id}/audit")

    async with create_test_client(database, sender) as other:
        await other.post(
            "/auth/signup",
            json={
                "email": "other-audit@example.com",
                "name": "Other",
                "password": "secure-passphrase",
            },
        )
        hidden = await other.get(f"/opportunities/{opportunity_id}/audit")

    assert [event["action"] for event in audit.json()] == [
        "opportunity_detected",
        "analysis_started",
        "analysis_completed",
        "pitch_generated",
        "pitch_approved",
        "pitch_sent",
    ]
    assert hidden.status_code == 404
