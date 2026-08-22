from pathlib import Path

import httpx

from pressradar.config import Settings
from pressradar.main import create_app


def create_test_client(database_path: Path) -> httpx.AsyncClient:
    app = create_app(Settings(database_path=str(database_path)))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_signup_creates_authenticated_workspace_identity(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "auth.db") as client:
        signup = await client.post(
            "/auth/signup",
            json={"email": "Owner@Example.com", "name": "Amina", "password": "secure-passphrase"},
        )
        identity = signup.json()
        current = await client.get("/auth/me")

    assert signup.status_code == 201
    assert "HttpOnly" in signup.headers["set-cookie"]
    assert identity["email"] == "owner@example.com"
    assert identity["workspace_id"]
    assert current.status_code == 200
    assert current.json() == identity


async def test_each_signup_receives_an_isolated_workspace(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "auth.db") as first_client:
        first = await first_client.post(
            "/auth/signup",
            json={"email": "first@example.com", "name": "First", "password": "first-password-123"},
        )
    async with create_test_client(tmp_path / "auth.db") as second_client:
        second = await second_client.post(
            "/auth/signup",
            json={
                "email": "second@example.com",
                "name": "Second",
                "password": "second-password-12",
            },
        )

    assert first.json()["workspace_id"] != second.json()["workspace_id"]


async def test_duplicate_email_is_rejected(tmp_path: Path) -> None:
    payload = {
        "email": "owner@example.com",
        "name": "Owner",
        "password": "secure-passphrase",
    }
    async with create_test_client(tmp_path / "auth.db") as client:
        assert (await client.post("/auth/signup", json=payload)).status_code == 201
        duplicate = await client.post("/auth/signup", json=payload)

    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "An account already uses this email"}


async def test_signin_uses_a_generic_error_for_unknown_accounts(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "auth.db") as client:
        response = await client.post(
            "/auth/signin",
            json={"email": "missing@example.com", "password": "incorrect"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


async def test_signout_revokes_the_session(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "auth.db") as client:
        await client.post(
            "/auth/signup",
            json={"email": "owner@example.com", "name": "Owner", "password": "secure-passphrase"},
        )
        signout = await client.post("/auth/signout")
        current = await client.get("/auth/me")

    assert signout.status_code == 204
    assert current.status_code == 401


async def test_signup_validates_email_name_and_password(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "auth.db") as client:
        response = await client.post(
            "/auth/signup",
            json={"email": "not-an-email", "name": "   ", "password": "short"},
        )

    assert response.status_code == 422
