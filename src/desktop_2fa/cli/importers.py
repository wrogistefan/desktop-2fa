"""Importers for various TOTP formats."""

import csv
import json
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List
from xml.etree import ElementTree as ET


def parse_aegis_json(content: str) -> List[Dict[str, Any]]:
    """Parse Aegis JSON export format.

    Args:
        content: JSON string content of the Aegis export.

    Returns:
        List of entry dictionaries with parsed TOTP data.
    """
    data = json.loads(content)
    entries = []
    for entry in data.get("entries", []):
        if entry.get("type") != "totp":
            continue

        issuer = entry.get("issuer", "")
        name = entry.get("name", "")
        info = entry.get("info", {})
        secret = info.get("secret", "")

        if not secret:
            continue

        entries.append(
            {
                "issuer": issuer,
                "account_name": name,
                "secret": secret,
                "digits": info.get("digits", 6),
                "period": info.get("period", 30),
                "algorithm": info.get("algorithm", "SHA1").upper(),
            }
        )

    return entries


def parse_bitwarden_csv(content: str) -> List[Dict[str, Any]]:
    """Parse Bitwarden CSV export format.

    Args:
        content: CSV string content of the Bitwarden export.

    Returns:
        List of entry dictionaries with parsed TOTP data.
    """
    reader = csv.DictReader(content.splitlines())
    entries: List[Dict[str, Any]] = []

    for row in reader:
        name = (row.get("name") or "").strip()
        totp = (row.get("totp") or "").strip()
        extras = row.get(None) or []

        issuer = name or ""

        # If there are 3 values → name, totp, extra
        #   issuer  = name
        #   account = totp
        #   secret  = extra
        # If there are 2 values → name, totp
        #   issuer  = name
        #   account = name
        #   secret  = totp
        if extras:
            account = totp or name or ""
            secret = extras[0].strip()
        else:
            account = name or ""
            secret = totp

        if not secret:
            continue

        entries.append(
            {
                "issuer": issuer,
                "account_name": account,
                "secret": secret,
                "digits": 6,
                "period": 30,
                "algorithm": "SHA1",
            }
        )

    return entries


def parse_1password_csv(content: str) -> List[Dict[str, Any]]:
    """Parse 1Password CSV export format.

    Args:
        content: CSV string content of the 1Password export.

    Returns:
        List of entry dictionaries with parsed TOTP data.
    """
    reader = csv.DictReader(content.splitlines())
    entries = []

    for row in reader:
        otp = (row.get("otp") or row.get("one-time password") or "").strip()
        if not otp:
            continue

        title = (row.get("title") or "").strip()

        entries.append(
            {
                "issuer": title,
                "account_name": title,
                "secret": otp,
                "digits": 6,
                "period": 30,
                "algorithm": "SHA1",
            }
        )

    return entries


def parse_otpauth_uri(uri: str) -> List[Dict[str, Any]]:
    """Parse otpauth:// URI format.

    Args:
        uri: The otpauth:// URI string.

    Returns:
        List of entry dictionaries with parsed TOTP data.

    Raises:
        ValueError: If the URI is invalid or not a TOTP URI.
    """
    if not uri.startswith("otpauth://"):
        raise ValueError("Invalid otpauth URI")

    parsed = urllib.parse.urlparse(uri)

    if parsed.scheme != "otpauth" or parsed.netloc != "totp":
        raise ValueError("Not a TOTP otpauth URI")

    path = parsed.path.lstrip("/")

    if ":" in path:
        issuer, account = path.split(":", 1)
    else:
        issuer = ""
        account = path

    query = urllib.parse.parse_qs(parsed.query)
    secret = query.get("secret", [""])[0]

    if not secret:
        raise ValueError("No secret in otpauth URI")

    digits = int(query.get("digits", ["6"])[0])
    period = int(query.get("period", ["30"])[0])
    algorithm = query.get("algorithm", ["SHA1"])[0].upper()

    return [
        {
            "issuer": issuer,
            "account_name": account,
            "secret": secret,
            "digits": digits,
            "period": period,
            "algorithm": algorithm,
        }
    ]


def parse_freeotp_xml(content: str) -> List[Dict[str, Any]]:
    """Parse FreeOTP XML export format.

    Args:
        content: XML string content of the FreeOTP export.

    Returns:
        List of entry dictionaries with parsed TOTP data.
    """
    root = ET.fromstring(content)
    entries = []

    for token in root.findall(".//token"):
        issuer = token.findtext("issuer", "")
        label = token.findtext("label", "")
        secret = token.findtext("secret", "")

        if not secret:
            continue

        if ":" in label:
            iss, acc = label.split(":", 1)
            issuer = iss
            account = acc
        else:
            account = label

        entries.append(
            {
                "issuer": issuer,
                "account_name": account,
                "secret": secret,
                "digits": 6,
                "period": 30,
                "algorithm": "SHA1",
            }
        )

    return entries


def import_from_format(format_name: str, source: str) -> List[Dict[str, Any]]:
    """Import entries from the given format and source.

    Args:
        format_name: The format name (aegis, bitwarden, 1password, otpauth, freeotp).
        source: File path or URI string depending on format.

    Returns:
        List of entry dictionaries with parsed TOTP data.

    Raises:
        ValueError: If the format is unsupported.
    """
    fmt = format_name.lower()

    if fmt == "aegis":
        return parse_aegis_json(Path(source).read_text())

    if fmt == "bitwarden":
        return parse_bitwarden_csv(Path(source).read_text())

    if fmt == "1password":
        return parse_1password_csv(Path(source).read_text())

    if fmt == "otpauth":
        return parse_otpauth_uri(source)

    if fmt == "freeotp":
        return parse_freeotp_xml(Path(source).read_text())

    raise ValueError(f"Unsupported format: {format_name}")
