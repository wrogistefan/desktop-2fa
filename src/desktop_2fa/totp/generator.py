"""TOTP code generation utilities."""

import hashlib
import hmac
import struct
import time

from ..utils.base32 import decode_base32


def generate(
    secret: str,
    timestamp: int | None = None,
    digits: int = 6,
    period: int = 30,
    algorithm: str = "SHA1",
) -> str:
    """Generate a TOTP code.

    Args:
        secret: The base32-encoded secret key.
        timestamp: The timestamp to use (defaults to current time).
        digits: Number of digits in the code (default 6).
        period: Time period in seconds (default 30).
        algorithm: Hash algorithm ('SHA1', 'SHA256', 'SHA512').

    Returns:
        The TOTP code as a string.

    Raises:
        InvalidSecret: If the Base32 secret is invalid or decodes to an empty key.
    """
    if timestamp is None:
        timestamp = int(time.time())

    counter = timestamp // period
    key = decode_base32(secret)

    algo = algorithm.casefold()
    if algo == "sha1":
        digestmod = hashlib.sha1
    elif algo == "sha256":
        digestmod = hashlib.sha256
    elif algo == "sha512":
        digestmod = hashlib.sha512
    else:
        raise ValueError("Unsupported algorithm")

    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, digestmod).digest()
    offset = h[-1] & 0x0F
    code = (struct.unpack(">I", h[offset : offset + 4])[0] & 0x7FFFFFFF) % (10**digits)

    return str(code).zfill(digits)
