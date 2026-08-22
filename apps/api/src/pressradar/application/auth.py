from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from pressradar.domain.auth import Identity


class DuplicateEmailError(Exception):
    """Raised when an email address already belongs to a user."""


class InvalidCredentialsError(Exception):
    """Raised when credentials cannot be authenticated."""


class AuthRepository(Protocol):
    def create_identity(self, *, email: str, name: str, password_hash: str) -> Identity: ...

    def find_credentials(self, email: str) -> tuple[Identity, str] | None: ...

    def create_session(self, *, token_hash: str, user_id: str, expires_at: datetime) -> None: ...

    def find_identity_by_session(self, *, token_hash: str, now: datetime) -> Identity | None: ...

    def delete_session(self, token_hash: str) -> None: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password_hash: str, password: str) -> bool: ...


class SessionTokens(Protocol):
    def create(self) -> tuple[str, str]: ...

    def hash(self, token: str) -> str: ...


@dataclass(frozen=True)
class AuthenticatedSession:
    identity: Identity
    token: str
    expires_at: datetime


class AuthService:
    def __init__(
        self,
        repository: AuthRepository,
        password_hasher: PasswordHasher,
        session_tokens: SessionTokens,
        session_ttl: timedelta,
    ) -> None:
        self._repository = repository
        self._password_hasher = password_hasher
        self._session_tokens = session_tokens
        self._session_ttl = session_ttl

    def sign_up(self, *, email: str, name: str, password: str) -> AuthenticatedSession:
        identity = self._repository.create_identity(
            email=email.strip().casefold(),
            name=name.strip(),
            password_hash=self._password_hasher.hash(password),
        )
        return self._start_session(identity)

    def sign_in(self, *, email: str, password: str) -> AuthenticatedSession:
        credentials = self._repository.find_credentials(email.strip().casefold())
        if credentials is None:
            raise InvalidCredentialsError
        identity, password_hash = credentials
        if not self._password_hasher.verify(password_hash, password):
            raise InvalidCredentialsError
        return self._start_session(identity)

    def authenticate(self, token: str) -> Identity | None:
        return self._repository.find_identity_by_session(
            token_hash=self._session_tokens.hash(token), now=datetime.now(UTC)
        )

    def sign_out(self, token: str) -> None:
        self._repository.delete_session(self._session_tokens.hash(token))

    def _start_session(self, identity: Identity) -> AuthenticatedSession:
        token, token_hash = self._session_tokens.create()
        expires_at = datetime.now(UTC) + self._session_ttl
        self._repository.create_session(
            token_hash=token_hash, user_id=identity.user_id, expires_at=expires_at
        )
        return AuthenticatedSession(identity=identity, token=token, expires_at=expires_at)
