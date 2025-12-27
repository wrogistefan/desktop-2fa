from desktop_2fa.totp.generator import generate


def test_rfc_vector_sha1() -> None:
    # RFC 6238 test vector
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
    assert generate(secret, timestamp=59) == "94287082"[-6:]


