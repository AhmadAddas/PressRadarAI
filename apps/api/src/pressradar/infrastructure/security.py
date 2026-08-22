import hashlib
import secrets

from argon2 import PasswordHasher as Argon2PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError


class PasswordHasher:
    def __init__(self) -> None:
        self._hasher = Argon2PasswordHasher()

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (InvalidHashError, VerifyMismatchError):
            return False


class SessionTokens:
    def create(self) -> tuple[str, str]:
        token = secrets.token_urlsafe(32)
        return token, self.hash(token)

    def hash(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
