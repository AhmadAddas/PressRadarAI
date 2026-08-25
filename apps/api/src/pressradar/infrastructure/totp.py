import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote


class TOTP:
    def create_secret(self) -> str:
        return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")

    def provisioning_uri(self, *, secret: str, email: str, issuer: str = "PressRadar") -> str:
        label = quote(f"{issuer}:{email}")
        return f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}&digits=6&period=30"

    def verify(self, *, secret: str, code: str, now: int | None = None) -> bool:
        if len(code) != 6 or not code.isdigit():
            return False
        timestamp = int(time.time()) if now is None else now
        return any(
            hmac.compare_digest(self._code(secret, timestamp + offset * 30), code)
            for offset in (-1, 0, 1)
        )

    @staticmethod
    def _code(secret: str, timestamp: int) -> str:
        padded = secret + "=" * (-len(secret) % 8)
        key = base64.b32decode(padded, casefold=True)
        digest = hmac.new(key, struct.pack(">Q", timestamp // 30), hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
        return f"{value % 1_000_000:06d}"
