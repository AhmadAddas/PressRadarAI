import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from pressradar.application.email import EmailDeliveryError, EmailMessage, EmailSender
from pressradar.domain.auth import Identity, WorkspaceKind


class DuplicateEmailError(Exception):
    """Raised when an email address already belongs to a user."""


class InvalidCredentialsError(Exception):
    """Raised when credentials cannot be authenticated."""


class TOTPRequiredError(Exception):
    """Raised when a valid authenticator code is required."""


class InvalidOTPError(Exception):
    """Raised when an email verification code is invalid or expired."""


class AuthRepository(Protocol):
    def create_identity(
        self, *, email: str, name: str, password_hash: str, email_verified: bool
    ) -> Identity: ...

    def find_credentials(self, email: str) -> tuple[Identity, str] | None: ...

    def find_identity(self, user_id: str) -> Identity | None: ...

    def verify_email(self, user_id: str) -> None: ...

    def delete_unverified_identity(self, user_id: str) -> None: ...

    def create_session(self, *, token_hash: str, user_id: str, expires_at: datetime) -> None: ...

    def find_identity_by_session(
        self, *, token_hash: str, now: datetime, workspace_kind: WorkspaceKind
    ) -> Identity | None: ...

    def delete_session(self, token_hash: str) -> None: ...

    def get_security(self, user_id: str) -> tuple[str | None, bool]: ...

    def save_totp(self, *, user_id: str, secret: str, enabled: bool) -> None: ...

    def complete_onboarding(self, user_id: str) -> None: ...

    def update_password(self, *, user_id: str, password_hash: str) -> None: ...

    def save_email_challenge(
        self,
        *,
        challenge_id: str,
        user_id: str,
        purpose: str,
        code_hash: str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> None: ...

    def consume_email_challenge(
        self, *, challenge_id: str, user_id: str, purpose: str, code_hash: str, now: datetime
    ) -> bool: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password_hash: str, password: str) -> bool: ...


class SessionTokens(Protocol):
    def create(self) -> tuple[str, str]: ...

    def hash(self, token: str) -> str: ...


class TOTPProvider(Protocol):
    def create_secret(self) -> str: ...

    def provisioning_uri(self, *, secret: str, email: str, issuer: str = "PressRadar") -> str: ...

    def verify(self, *, secret: str, code: str, now: int | None = None) -> bool: ...


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
        totp: TOTPProvider,
        email_sender: EmailSender,
        email_verification_required: bool = False,
    ) -> None:
        self._repository = repository
        self._password_hasher = password_hasher
        self._session_tokens = session_tokens
        self._session_ttl = session_ttl
        self._totp = totp
        self._email_sender = email_sender
        self._email_verification_required = email_verification_required

    @property
    def requires_email_verification(self) -> bool:
        return self._email_verification_required

    def sign_up(self, *, email: str, name: str, password: str) -> AuthenticatedSession:
        identity = self._repository.create_identity(
            email=email.strip().casefold(),
            name=name.strip(),
            password_hash=self._password_hasher.hash(password),
            email_verified=True,
        )
        return self._start_session(identity)

    def begin_sign_up(self, *, email: str, name: str, password: str) -> tuple[str, str]:
        identity = self._repository.create_identity(
            email=email.strip().casefold(),
            name=name.strip(),
            password_hash=self._password_hasher.hash(password),
            email_verified=False,
        )
        try:
            challenge = self.request_security_otp(identity, "verify_email")
        except EmailDeliveryError:
            self._repository.delete_unverified_identity(identity.user_id)
            raise
        return identity.user_id, challenge

    def verify_sign_up(self, *, user_id: str, challenge_id: str, code: str) -> AuthenticatedSession:
        identity = self._repository.find_identity(user_id)
        if identity is None:
            raise InvalidOTPError
        self.verify_security_otp(
            identity, challenge_id=challenge_id, code=code, purpose="verify_email"
        )
        self._repository.verify_email(user_id)
        return self._start_session(identity)

    def sign_in(
        self, *, email: str, password: str, totp_code: str | None = None
    ) -> AuthenticatedSession:
        credentials = self._repository.find_credentials(email.strip().casefold())
        if credentials is None:
            raise InvalidCredentialsError
        identity, password_hash = credentials
        if not self._password_hasher.verify(password_hash, password):
            raise InvalidCredentialsError
        secret, enabled = self._repository.get_security(identity.user_id)
        if enabled and (
            secret is None or not self._totp.verify(secret=secret, code=totp_code or "")
        ):
            raise TOTPRequiredError
        return self._start_session(identity)

    def begin_totp_setup(self, identity: Identity) -> tuple[str, str]:
        secret = self._totp.create_secret()
        self._repository.save_totp(user_id=identity.user_id, secret=secret, enabled=False)
        return secret, self._totp.provisioning_uri(secret=secret, email=identity.email)

    def enable_totp(self, identity: Identity, code: str) -> None:
        secret, _ = self._repository.get_security(identity.user_id)
        if secret is None or not self._totp.verify(secret=secret, code=code):
            raise TOTPRequiredError
        self._repository.save_totp(user_id=identity.user_id, secret=secret, enabled=True)
        self._repository.complete_onboarding(identity.user_id)

    def skip_totp(self, identity: Identity) -> None:
        self._repository.complete_onboarding(identity.user_id)

    def change_password(self, identity: Identity, current: str, new: str) -> None:
        credentials = self._repository.find_credentials(identity.email)
        if credentials is None or not self._password_hasher.verify(credentials[1], current):
            raise InvalidCredentialsError
        self._repository.update_password(
            user_id=identity.user_id, password_hash=self._password_hasher.hash(new)
        )

    def request_security_otp(self, identity: Identity, purpose: str) -> str:
        challenge_id = secrets.token_urlsafe(24)
        code = f"{secrets.randbelow(1_000_000):06d}"
        issued_at = datetime.now(UTC)
        email_context = {
            "verify_email": ("email verification", "verify your email address"),
            "setup_2fa": ("2FA setup", "set up or change two-factor authentication"),
            "disable_2fa": ("2FA deactivation", "deactivate two-factor authentication"),
        }.get(purpose, ("security verification", "complete your security request"))
        self._repository.save_email_challenge(
            challenge_id=challenge_id,
            user_id=identity.user_id,
            purpose=purpose,
            code_hash=self._session_tokens.hash(code),
            issued_at=issued_at,
            expires_at=issued_at + timedelta(minutes=10),
        )
        self._email_sender.send(
            EmailMessage(
                recipient=identity.email,
                subject=f"PressRadar {email_context[0]} code",
                text=(
                    f"Use code {code} to {email_context[1]}. "
                    "This code expires in 10 minutes. Use only the newest code for this action."
                ),
            )
        )
        return challenge_id

    def verify_security_otp(
        self, identity: Identity, *, challenge_id: str, code: str, purpose: str
    ) -> None:
        if not self._repository.consume_email_challenge(
            challenge_id=challenge_id,
            user_id=identity.user_id,
            purpose=purpose,
            code_hash=self._session_tokens.hash(code),
            now=datetime.now(UTC),
        ):
            raise InvalidOTPError

    def disable_totp(self, identity: Identity) -> None:
        self._repository.save_totp(user_id=identity.user_id, secret="", enabled=False)

    def authenticate(
        self, token: str, workspace_kind: WorkspaceKind = WorkspaceKind.PROD
    ) -> Identity | None:
        return self._repository.find_identity_by_session(
            token_hash=self._session_tokens.hash(token),
            now=datetime.now(UTC),
            workspace_kind=workspace_kind,
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
