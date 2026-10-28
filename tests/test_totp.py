import base64

import pytest

from desktop_2fa.totp.generator import generate

SECRET = "JBSWY3DPEHPK3PXP"  # poprawny base32

# RFC 6238 Appendix B; Appendix A specifies 20/32/64-byte ASCII keys.
# https://www.rfc-editor.org/rfc/rfc6238#appendix-B
RFC_SECRETS = {
    "SHA1": b"12345678901234567890",
    "SHA256": b"12345678901234567890123456789012",
    "SHA512": b"1234567890123456789012345678901234567890123456789012345678901234",
}
RFC_VECTORS = [
    (59, "94287082", "46119246", "90693936"),
    (1111111109, "07081804", "68084774", "25091201"),
    (1111111111, "14050471", "67062674", "99943326"),
    (1234567890, "89005924", "91819424", "93441116"),
    (2000000000, "69279037", "90698825", "38618901"),
    (20000000000, "65353130", "77737706", "47863826"),
]


@pytest.mark.parametrize("timestamp,sha1,sha256,sha512", RFC_VECTORS)
@pytest.mark.parametrize("algorithm", ["SHA1", "SHA256", "SHA512"])
def test_rfc6238_vectors(
    timestamp: int, sha1: str, sha256: str, sha512: str, algorithm: str
) -> None:
    expected = dict(SHA1=sha1, SHA256=sha256, SHA512=sha512)[algorithm]
    secret = base64.b32encode(RFC_SECRETS[algorithm]).decode("ascii")
    assert (
        generate(secret, timestamp=timestamp, digits=8, period=30, algorithm=algorithm)
        == expected
    )


@pytest.mark.parametrize("period", [30, 45, 60])
@pytest.mark.parametrize(
    "timestamp_step,expected", [(0, "84755224"), (1, "94287082"), (2, "37359152")]
)
@pytest.mark.parametrize("edge", [0, -1])
def test_period_boundaries(
    period: int, timestamp_step: int, expected: str, edge: int
) -> None:
    # Start and final second of each step; expected HOTP counters 0, 1, 2.
    timestamp = (
        timestamp_step * period if edge == 0 else (timestamp_step + 1) * period - 1
    )
    secret = base64.b32encode(RFC_SECRETS["SHA1"]).decode("ascii")
    assert generate(secret, timestamp=timestamp, digits=8, period=period) == expected


@pytest.mark.parametrize(
    "digits,expected", [(6, "081804"), (7, "7081804"), (8, "07081804")]
)
def test_exact_digits_and_leading_zero(digits: int, expected: str) -> None:
    secret = base64.b32encode(RFC_SECRETS["SHA1"]).decode("ascii")
    assert generate(secret, timestamp=1111111109, digits=digits) == expected


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
