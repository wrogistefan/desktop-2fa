import pytest

from desktop_2fa.totp.generator import generate

SECRET = "JBSWY3DPEHPK3PXP"  # poprawny base32


def test_totp_sha1_deterministic() -> None:
    code1 = generate(SECRET, timestamp=0, digits=6, period=30, algorithm="SHA1")
    code2 = generate(SECRET, timestamp=0, digits=6, period=30, algorithm="SHA1")

    assert code1 == code2
    assert len(code1) == 6
    assert code1.isdigit()


def test_totp_different_time_produces_different_code() -> None:
    code1 = generate(SECRET, timestamp=0, digits=6, period=30, algorithm="SHA1")
    code2 = generate(SECRET, timestamp=60, digits=6, period=30, algorithm="SHA1")

    assert code1 != code2


def test_totp_sha256_and_sha512() -> None:
    code256 = generate(SECRET, timestamp=0, digits=6, period=30, algorithm="SHA256")
    code512 = generate(SECRET, timestamp=0, digits=6, period=30, algorithm="SHA512")

    assert len(code256) == 6
    assert len(code512) == 6
    assert code256.isdigit()
    assert code512.isdigit()
    # raczej różne od SHA1 dla tego samego czasu
    code1 = generate(SECRET, timestamp=0, digits=6, period=30, algorithm="SHA1")
    assert code256 != code1 or code512 != code1


def test_totp_different_digits() -> None:
    code6 = generate(SECRET, timestamp=0, digits=6, period=30, algorithm="SHA1")
    code8 = generate(SECRET, timestamp=0, digits=8, period=30, algorithm="SHA1")

    assert len(code6) == 6
    assert len(code8) == 8
    assert code6.isdigit()
    assert code8.isdigit()


def test_totp_unsupported_algorithm() -> None:
    with pytest.raises(ValueError):
        generate(SECRET, timestamp=0, digits=6, period=30, algorithm="MD5")
