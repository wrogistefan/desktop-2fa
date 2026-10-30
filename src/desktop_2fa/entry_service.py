"""Shared entry operations; prompting and rendering belong to callers."""

import re
import time
import urllib.parse
from pathlib import Path
from typing import Literal, TypedDict, cast

from desktop_2fa.totp.generator import generate
from desktop_2fa.utils.base32 import normalize_base32
from desktop_2fa.vault import Vault
from desktop_2fa.vault.models import TotpEntry


class TotpParameters(TypedDict):
    algorithm: Literal["SHA1", "SHA256", "SHA512"]
    digits: Literal[6, 7, 8]
    period: int


class ParsedOtpauth(TotpParameters):
    issuer: str
    label: str
    secret: str


def parse_otpauth_url(url: str) -> ParsedOtpauth:
    """Validate TOTP provisioning data without dropping code parameters."""
    if not url.startswith("otpauth://"):
        raise ValueError("Invalid otpauth URL")

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "otpauth" or parsed.netloc != "totp":
        raise ValueError("Only TOTP otpauth URLs are supported")

    if parsed.fragment or re.search(r"%(?![0-9a-fA-F]{2})", url):
        raise ValueError("Invalid otpauth URL encoding or fragment")
    path = urllib.parse.unquote(parsed.path.removeprefix("/"), errors="strict")
    if ":" in path:
        prefix, label = path.split(":", 1)
        label = label.lstrip(" ")
        if ":" in label:
            raise ValueError("Issuer and account label cannot contain colons")
    else:
        prefix = ""
        label = path
    if not label:
        raise ValueError("Account label is required")

    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True, errors="strict")
    for parameter in ("secret", "issuer", "algorithm", "digits", "period", "counter"):
        if len(query.get(parameter, [])) > 1:
            raise ValueError(f"Duplicate {parameter} parameter")
    if "counter" in query:
        raise ValueError("Counter is not supported for TOTP provisioning")
    secret = query.get("secret", [""])[0]
    if not secret:
        raise ValueError("Secret parameter is required")

    url_issuer = query.get("issuer", [""])[0]
    if "issuer" in query and not url_issuer:
        raise ValueError("Issuer parameter cannot be empty")
    if ":" in url_issuer:
        raise ValueError("Issuer cannot contain colons")
    if prefix and url_issuer and prefix != url_issuer:
        raise ValueError("Issuer parameter conflicts with the label prefix")
    issuer = url_issuer or prefix or (label if ":" not in path else "Unknown")

    algorithm = query.get("algorithm", ["SHA1"])[0].upper()
    if algorithm not in ("SHA1", "SHA256", "SHA512"):
        raise ValueError("Unsupported algorithm (expected SHA1, SHA256 or SHA512)")
    digits = query.get("digits", ["6"])[0]
    if digits not in ("6", "7", "8"):
        raise ValueError("Invalid digits (expected 6, 7 or 8)")
    period = query.get("period", ["30"])[0]
    if not period.isascii() or not period.isdecimal() or int(period) <= 0:
        raise ValueError("Period must be a positive integer")

    return {
        "issuer": issuer,
        "label": label,
        "secret": normalize_base32(secret),
        "algorithm": cast(Literal["SHA1", "SHA256", "SHA512"], algorithm),
        "digits": cast(Literal[6, 7, 8], int(digits)),
        "period": int(period),
    }


def prepare_add(name: str, issuer: str, secret: str) -> ParsedOtpauth:
    """Validate provisioning input before any vault load or mutation."""
    if issuer.startswith("otpauth://"):
        if secret:
            raise ValueError("Do not combine an otpauth URL with a separate secret")
        return parse_otpauth_url(issuer)
    return {
        "label": name,
        "issuer": issuer,
        "secret": normalize_base32(secret),
        "algorithm": "SHA1",
        "digits": 6,
        "period": 30,
    }


def add_prepared(vault: Vault, parsed: ParsedOtpauth) -> None:
    """Apply validated input using Vault's collision and model validation."""
    vault.add_entry(
        name=parsed["label"],
        issuer=parsed["issuer"],
        secret=parsed["secret"],
        algorithm=parsed["algorithm"],
        digits=parsed["digits"],
        period=parsed["period"],
    )


def rename_and_save(
    vault: Vault,
    path: Path,
    password: str,
    old: str,
    new: str,
    *,
    index: int | None = None,
) -> None:
    """Use the same selector, collision checks and revision-aware save everywhere."""
    vault.rename_entry(old, new, index=index)
    vault.save(path, password)


def generate_code(
    vault: Vault,
    name: str,
    *,
    timestamp: int | None = None,
) -> tuple[TotpEntry, str, int]:
    """Resolve once and generate with the selected entry's exact parameters."""
    entry = vault.get_entry(name)
    if timestamp is None:
        timestamp = int(time.time())
    code = generate(
        secret=entry.secret,
        timestamp=timestamp,
        digits=entry.digits,
        period=entry.period,
        algorithm=entry.algorithm,
    )
    return entry, code, entry.period - timestamp % entry.period
