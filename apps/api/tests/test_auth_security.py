import asyncio
import re
import time
from pathlib import Path

import httpx
from pydantic import SecretStr

from pressradar.application.email import EmailMessage
from pressradar.config import Settings
from pressradar.infrastructure.totp import TOTP
from pressradar.main import create_app


class RecordingEmailSender:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> str:
        self.messages.append(message)
        return f"message-{len(self.messages)}"


def otp(message: EmailMessage) -> str:
    match = re.search(r"\b(\d{6})\b", message.text)
    assert match is not None
    return match.group(1)


def secure_client(database: Path, sender: RecordingEmailSender) -> httpx.AsyncClient:
    app = create_app(
        Settings(
            database_path=str(database),
            email_provider="nodemailer",
            mailer_internal_token=SecretStr("internal-test-token"),
            ai_provider="fake",
        ),
        email_sender=sender,
    )
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_verified_signup_totp_password_and_email_authorized_deactivation(
    tmp_path: Path,
) -> None:
    sender = RecordingEmailSender()
    async with secure_client(tmp_path / "security.db", sender) as client:
        started = await client.post(
            "/auth/signup",
            json={
                "email": "Owner@Example.com",
                "name": "Amina Owner",
                "password": "secure-passphrase",
            },
        )
        assert started.status_code == 202
        assert (await client.get("/auth/me")).status_code == 401
        challenge = started.json()
        verified = await client.post(
            "/auth/signup/verify",
            json={
                "user_id": challenge["user_id"],
                "challenge_id": challenge["challenge_id"],
                "code": otp(sender.messages[-1]),
            },
        )
        assert verified.status_code == 200
        assert verified.json()["onboarding_completed"] is False

        setup = await client.post("/auth/2fa/setup")
        secret = setup.json()["secret"]
        assert secret in setup.json()["provisioning_uri"]
        authenticator_code = TOTP._code(secret, int(time.time()))
        assert (
            await client.post("/auth/2fa/enable", json={"code": authenticator_code})
        ).status_code == 204

        assert (
            await client.post(
                "/auth/password",
                json={
                    "current_password": "secure-passphrase",
                    "new_password": "new-secure-passphrase",
                },
            )
        ).status_code == 204
        await client.post("/auth/signout")
        missing_totp = await client.post(
            "/auth/signin",
            json={"email": "owner@example.com", "password": "new-secure-passphrase"},
        )
        assert missing_totp.status_code == 428
        signed_in = await client.post(
            "/auth/signin",
            json={
                "email": "owner@example.com",
                "password": "new-secure-passphrase",
                "totp_code": TOTP._code(secret, int(time.time())),
            },
        )
        assert signed_in.status_code == 200

        requested = await client.post("/auth/2fa/email-code", json={"purpose": "disable_2fa"})
        assert sender.messages[-1].subject.startswith("PressRadar 2FA deactivation code [")
        assert "Reference:" in sender.messages[-1].text
        assert "Use only the newest code for this action" in sender.messages[-1].text
        disabled = await client.post(
            "/auth/2fa/disable",
            json={
                "challenge_id": requested.json()["challenge_id"],
                "code": otp(sender.messages[-1]),
            },
        )
        assert disabled.status_code == 204
        assert (await client.get("/auth/me")).json()["totp_enabled"] is False


async def test_email_verification_code_is_single_use(tmp_path: Path) -> None:
    sender = RecordingEmailSender()
    async with secure_client(tmp_path / "single-use.db", sender) as client:
        started = await client.post(
            "/auth/signup",
            json={
                "email": "single@example.com",
                "name": "Single Use",
                "password": "secure-passphrase",
            },
        )
        request = {
            "user_id": started.json()["user_id"],
            "challenge_id": started.json()["challenge_id"],
            "code": otp(sender.messages[-1]),
        }
        assert (await client.post("/auth/signup/verify", json=request)).status_code == 200
        assert (await client.post("/auth/signup/verify", json=request)).status_code == 400


async def test_concurrent_email_verification_consumes_code_once(tmp_path: Path) -> None:
    sender = RecordingEmailSender()
    async with secure_client(tmp_path / "concurrent-code.db", sender) as client:
        started = await client.post(
            "/auth/signup",
            json={
                "email": "concurrent@example.com",
                "name": "Concurrent User",
                "password": "secure-passphrase",
            },
        )
        request = {
            "user_id": started.json()["user_id"],
            "challenge_id": started.json()["challenge_id"],
            "code": otp(sender.messages[-1]),
        }
        responses = await asyncio.gather(
            client.post("/auth/signup/verify", json=request),
            client.post("/auth/signup/verify", json=request),
        )

    assert sorted(response.status_code for response in responses) == [200, 400]


async def test_new_security_code_invalidates_previous_active_code(tmp_path: Path) -> None:
    sender = RecordingEmailSender()
    async with secure_client(tmp_path / "superseded-code.db", sender) as client:
        started = await client.post(
            "/auth/signup",
            json={
                "email": "superseded@example.com",
                "name": "Superseded Code",
                "password": "secure-passphrase",
            },
        )
        assert (
            await client.post(
                "/auth/signup/verify",
                json={
                    "user_id": started.json()["user_id"],
                    "challenge_id": started.json()["challenge_id"],
                    "code": otp(sender.messages[-1]),
                },
            )
        ).status_code == 200
        assert (await client.post("/auth/2fa/skip")).status_code == 204

        first = await client.post("/auth/2fa/email-code", json={"purpose": "setup_2fa"})
        first_code = otp(sender.messages[-1])
        second = await client.post("/auth/2fa/email-code", json={"purpose": "setup_2fa"})
        second_code = otp(sender.messages[-1])

        assert (
            await client.post(
                "/auth/2fa/setup",
                json={"challenge_id": first.json()["challenge_id"], "code": first_code},
            )
        ).status_code == 400
        assert (
            await client.post(
                "/auth/2fa/setup",
                json={"challenge_id": second.json()["challenge_id"], "code": second_code},
            )
        ).status_code == 200
