"""Shared Base32 rules for TOTP input, stored models and code generation."""

import base64
import binascii


class InvalidSecret(ValueError):
    """Raised for invalid or empty TOTP key material without exposing it."""


def decode_base32(secret: str, *, allow_empty: bool = False) -> bytes:
    """Decode ASCII Base32, ignoring ASCII spaces and accepting omitted padding.

    ASCII lowercase is accepted. Supplied padding must be correct and trailing;
    other whitespace, Unicode folding and alphabet substitutions are rejected.
    Empty keys are allowed only for validation of historical stored models.
    """
    if not isinstance(secret, str):
        raise InvalidSecret("Invalid Base32 TOTP secret")
    cleaned = secret.replace(" ", "")
    if "=" not in cleaned:
        cleaned += "=" * (-len(cleaned) % 8)
    try:
        decoded = base64.b32decode(cleaned, casefold=True)
    except (ValueError, binascii.Error):
        raise InvalidSecret("Invalid Base32 TOTP secret") from None
    if not decoded and not allow_empty:
        raise InvalidSecret("Invalid Base32 TOTP secret: a non-empty key is required")
    return decoded


def normalize_base32(secret: str) -> str:
    """Return canonical uppercase, padded Base32 for a non-empty decoded key."""
    return base64.b32encode(decode_base32(secret)).decode("ascii")
