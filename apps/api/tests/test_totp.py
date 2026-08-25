from pressradar.infrastructure.totp import TOTP


def test_totp_verifies_current_code_and_builds_manual_setup_uri() -> None:
    totp = TOTP()
    secret = "JBSWY3DPEHPK3PXP"
    code = totp._code(secret, 1_700_000_000)

    assert totp.verify(secret=secret, code=code, now=1_700_000_000)
    assert not totp.verify(secret=secret, code="000000", now=1_700_000_000)
    assert totp.provisioning_uri(secret=secret, email="owner@example.com") == (
        "otpauth://totp/PressRadar%3Aowner%40example.com?"
        "secret=JBSWY3DPEHPK3PXP&issuer=PressRadar&digits=6&period=30"
    )
