"""Explicit, validated TOTP adapters; these are not wired into CLI import."""

import csv
import io
import json
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from desktop_2fa.utils.base32 import normalize_base32
from desktop_2fa.vault.models import TotpEntry

from .helpers import parse_otpauth_url


class ImportFormatError(ValueError):
    """Unsupported or malformed export; messages never include input values."""


def _validated(**values: Any) -> dict[str, Any]:
    try:
        values["secret"] = normalize_base32(values["secret"])
        return TotpEntry.model_validate(values).model_dump()
    except (ValueError, TypeError):
        raise ImportFormatError("Invalid TOTP record in export") from None


def _nonempty(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not entries:
        raise ImportFormatError("Export contains no TOTP entries")
    return entries


def parse_aegis_json(content: str) -> list[dict[str, Any]]:
    """Read plaintext Aegis v1 envelopes and database versions 1, 2 or 3.

    Unsupported OTP types and malformed records abort the complete conversion.
    Only TOTP fields are converted; groups, notes and icons are not imported.
    """
    try:
        data = json.loads(content.removeprefix("\ufeff"))
    except (ValueError, TypeError):
        raise ImportFormatError("Invalid Aegis JSON") from None
    if (
        not isinstance(data, dict)
        or type(data.get("version")) is not int
        or data["version"] != 1
    ):
        raise ImportFormatError("Unsupported Aegis envelope")
    header, database = data.get("header"), data.get("db")
    if isinstance(database, str):
        raise ImportFormatError("Encrypted Aegis exports are not supported")
    if (
        not isinstance(header, dict)
        or header.get("slots") is not None
        or header.get("params") is not None
    ):
        raise ImportFormatError("Unsupported or encrypted Aegis header")
    if (
        not isinstance(database, dict)
        or type(database.get("version")) is not int
        or database["version"] not in (1, 2, 3)
    ):
        raise ImportFormatError("Unsupported Aegis database")
    records = database.get("entries")
    if not isinstance(records, list):
        raise ImportFormatError("Aegis database entries must be a list")
    entries = []
    for record in records:
        if not isinstance(record, dict) or record.get("type") != "totp":
            raise ImportFormatError("Unsupported Aegis OTP record type")
        info = record.get("info")
        if (
            not isinstance(info, dict)
            or {"secret", "algo", "digits", "period"} != info.keys()
        ):
            raise ImportFormatError("Missing or unsupported Aegis TOTP parameters")
        if (
            not isinstance(info["algo"], str)
            or type(info["digits"]) is not int
            or type(info["period"]) is not int
        ):
            raise ImportFormatError("Invalid Aegis TOTP parameters")
        entries.append(
            _validated(
                issuer=record.get("issuer", ""),
                account_name=record.get("name", ""),
                secret=info["secret"],
                algorithm=info["algo"].upper(),
                digits=info["digits"],
                period=info["period"],
            )
        )
    return _nonempty(entries)


def _csv_rows(content: str) -> tuple[set[str], list[dict[str, str]]]:
    try:
        reader = csv.reader(
            io.StringIO(content.removeprefix("\ufeff"), newline=""), strict=True
        )
        headers = [field.strip().casefold() for field in next(reader)]
        if not headers or "" in headers or len(headers) != len(set(headers)):
            raise ImportFormatError("Invalid or duplicate CSV headers")
        rows = []
        for row in reader:
            if not row:
                continue
            if len(row) != len(headers):
                raise ImportFormatError("CSV row does not match its headers")
            rows.append(dict(zip(headers, row, strict=True)))
        return set(headers), rows
    except (csv.Error, StopIteration):
        raise ImportFormatError("Invalid CSV export") from None


def parse_otpauth_uri(uri: str) -> list[dict[str, Any]]:
    """Use the shared provisioning parser, retaining its exact parameters."""
    try:
        parsed = parse_otpauth_url(uri)
    except (ValueError, TypeError):
        raise ImportFormatError("Invalid TOTP provisioning URI") from None
    return [
        _validated(
            issuer=parsed["issuer"],
            account_name=parsed["label"],
            secret=parsed["secret"],
            algorithm=parsed["algorithm"],
            digits=parsed["digits"],
            period=parsed["period"],
        )
    ]


def _otp_cell(value: str, issuer: str, account: str) -> dict[str, Any]:
    if value.startswith("otpauth://"):
        return parse_otpauth_uri(value)[0]
    return _validated(issuer=issuer, account_name=account, secret=value)


def parse_bitwarden_csv(content: str) -> list[dict[str, Any]]:
    """Read login_totp cells; URI labels win, bare keys use CSV identity.

    Rows without a token are ignored. A token on a non-login row, malformed
    token or unsupported OTP type aborts the whole conversion.
    """
    headers, rows = _csv_rows(content)
    if not {"name", "login_totp"} <= headers:
        raise ImportFormatError("Unsupported Bitwarden CSV headers")
    entries = []
    for row in rows:
        if not row["login_totp"]:
            continue
        if row.get("type", "login").casefold() != "login":
            raise ImportFormatError("Unsupported Bitwarden record type with OTP")
        entries.append(
            _otp_cell(
                row["login_totp"], row["name"], row.get("login_username") or row["name"]
            )
        )
    return _nonempty(entries)


def parse_1password_csv(content: str) -> list[dict[str, Any]]:
    """Read title plus one OTP column; see docs/import_adapters.md for variants."""
    headers, rows = _csv_rows(content)
    otp_columns = headers & {"otp", "one-time password"}
    if "title" not in headers or len(otp_columns) != 1:
        raise ImportFormatError("Unsupported or ambiguous 1Password CSV headers")
    column = next(iter(otp_columns))
    entries = [
        _otp_cell(row[column], row["title"], row.get("username") or row["title"])
        for row in rows
        if row[column]
    ]
    return _nonempty(entries)


def parse_freeotp_xml(content: str) -> list[dict[str, Any]]:
    """Read only the legacy custom tokens/token XML, not native FreeOTP backups."""
    if "<!DOCTYPE" in content.upper() or "<!ENTITY" in content.upper():
        raise ImportFormatError("XML declarations are not supported")
    try:
        root = ET.fromstring(content)
    except (ET.ParseError, ValueError, LookupError):
        raise ImportFormatError("Invalid XML export") from None
    if root.tag != "tokens" or root.attrib:
        raise ImportFormatError(
            "Unsupported FreeOTP XML variant; native backups are not supported"
        )
    entries = []
    for token in root:
        tags = [field.tag for field in token]
        if (
            token.tag != "token"
            or token.attrib
            or len(tags) != len(set(tags))
            or not set(tags) <= {"issuer", "label", "secret"}
            or any(field.attrib or len(field) for field in token)
        ):
            raise ImportFormatError("Unsupported legacy XML token structure")
        issuer, label = token.findtext("issuer", ""), token.findtext("label", "")
        if ":" in label:
            prefix, account = label.split(":", 1)
            if issuer and issuer != prefix:
                raise ImportFormatError("Conflicting legacy XML labels")
            issuer = prefix
        else:
            account = label
        entries.append(
            _validated(
                issuer=issuer, account_name=account, secret=token.findtext("secret", "")
            )
        )
    return _nonempty(entries)


def import_from_format(format_name: str, source: str) -> list[dict[str, Any]]:
    """Parse a selected UTF-8 export; never read the default vault or persist data."""
    if format_name.casefold() == "otpauth":
        return parse_otpauth_uri(source)
    parsers = {
        "aegis": parse_aegis_json,
        "bitwarden": parse_bitwarden_csv,
        "1password": parse_1password_csv,
        "freeotp": parse_freeotp_xml,
    }
    parser = parsers.get(format_name.casefold())
    if parser is None:
        raise ImportFormatError("Unsupported format")
    try:
        with Path(source).open("r", encoding="utf-8-sig", newline="") as stream:
            content = stream.read()
    except UnicodeError:
        raise ImportFormatError("Export must use UTF-8") from None
    return parser(content)
