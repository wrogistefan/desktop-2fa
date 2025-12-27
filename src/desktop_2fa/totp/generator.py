import base64
import hashlib
import hmac
import struct
import time


def generate(
    secret: str,
    timestamp: int | None = None,
    digits: int = 6,
    period: int = 30,
    algorithm: str = "SHA1",
) -> str:
    if timestamp is None:
        timestamp = int(time.time())

    counter = timestamp // period
    key = base64.b32decode(secret, casefold=True)

    if algorithm.upper() == "SHA1":
        digestmod = hashlib.sha1
    elif algorithm.upper() == "SHA256":
        digestmod = hashlib.sha256
    elif algorithm.upper() == "SHA512":
        digestmod = hashlib.sha512
    else:
        raise ValueError("Unsupported algorithm")

    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, digestmod).digest()
    offset = h[-1] & 0x0F
    code = (struct.unpack(">I", h[offset : offset + 4])[0] & 0x7FFFFFFF) % (10**digits)

    return str(code).zfill(digits)
