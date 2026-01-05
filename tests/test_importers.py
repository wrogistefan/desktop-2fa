import pathlib

import pytest

from desktop_2fa.cli.importers import (
    import_from_format,
    parse_1password_csv,
    parse_aegis_json,
    parse_bitwarden_csv,
    parse_freeotp_xml,
    parse_otpauth_uri,
)


def test_parse_aegis_json() -> None:
    content = """{
        "entries": [
            {
                "type": "totp",
                "issuer": "GitHub",
                "name": "user@github.com",
                "info": {
                    "secret": "JBSWY3DPEHPK3PXP",
                    "digits": 6,
                    "period": 30,
                    "algorithm": "SHA1"
                }
            },
            {
                "type": "hotp",
                "issuer": "Test",
                "name": "test",
                "info": {
                    "secret": "SECRET2"
                }
            },
            {
                "type": "totp",
                "issuer": "Empty",
                "name": "empty",
                "info": {
                    "secret": ""
                }
            }
        ]
    }"""

    entries = parse_aegis_json(content)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["issuer"] == "GitHub"
    assert entry["account_name"] == "user@github.com"
    assert entry["secret"] == "JBSWY3DPEHPK3PXP"
    assert entry["digits"] == 6
    assert entry["period"] == 30
    assert entry["algorithm"] == "SHA1"


def test_parse_bitwarden_csv() -> None:
    content = """name,totp
GitHub,user@github.com,JBSWY3DPEHPK3PXP
Google,test@gmail.com,JBSWY3DPEHPK3PXS
Simple,JBSWY3DPEHPK3PXT
Empty,"""

    entries = parse_bitwarden_csv(content)
    assert len(entries) == 3

    # First entry with colon
    assert entries[0]["issuer"] == "GitHub"
    assert entries[0]["account_name"] == "user@github.com"
    assert entries[0]["secret"] == "JBSWY3DPEHPK3PXP"

    # Second entry with colon
    assert entries[1]["issuer"] == "Google"
    assert entries[1]["account_name"] == "test@gmail.com"
    assert entries[1]["secret"] == "JBSWY3DPEHPK3PXS"

    # Third entry without colon
    assert entries[2]["issuer"] == "Simple"
    assert entries[2]["account_name"] == "Simple"
    assert entries[2]["secret"] == "JBSWY3DPEHPK3PXT"


def test_parse_1password_csv() -> None:
    content = """title,otp
GitHub,JBSWY3DPEHPK3PXP
Google:test@gmail.com,JBSWY3DPEHPK3PXS
Empty,"""

    entries = parse_1password_csv(content)
    assert len(entries) == 2

    assert entries[0]["issuer"] == "GitHub"
    assert entries[0]["account_name"] == "GitHub"
    assert entries[0]["secret"] == "JBSWY3DPEHPK3PXP"

    assert entries[1]["issuer"] == "Google:test@gmail.com"
    assert entries[1]["account_name"] == "Google:test@gmail.com"
    assert entries[1]["secret"] == "JBSWY3DPEHPK3PXS"


def test_parse_otpauth_uri() -> None:
    uri = "otpauth://totp/GitHub:user@github.com?secret=JBSWY3DPEHPK3PXP&digits=6&period=30&algorithm=SHA1"

    entries = parse_otpauth_uri(uri)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["issuer"] == "GitHub"
    assert entry["account_name"] == "user@github.com"
    assert entry["secret"] == "JBSWY3DPEHPK3PXP"
    assert entry["digits"] == 6
    assert entry["period"] == 30
    assert entry["algorithm"] == "SHA1"


def test_parse_otpauth_uri_no_issuer() -> None:
    uri = "otpauth://totp/user@github.com?secret=JBSWY3DPEHPK3PXP"

    entries = parse_otpauth_uri(uri)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["issuer"] == ""
    assert entry["account_name"] == "user@github.com"
    assert entry["secret"] == "JBSWY3DPEHPK3PXP"


def test_parse_otpauth_uri_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid otpauth URI"):
        parse_otpauth_uri("https://example.com")

    with pytest.raises(ValueError, match="Not a TOTP otpauth URI"):
        parse_otpauth_uri("otpauth://hotp/GitHub:user?secret=SECRET")

    with pytest.raises(ValueError, match="No secret in otpauth URI"):
        parse_otpauth_uri("otpauth://totp/GitHub:user")


def test_parse_freeotp_xml() -> None:
    content = """<?xml version="1.0" encoding="utf-8"?>
<tokens>
    <token>
        <issuer>GitHub</issuer>
        <label>user@github.com</label>
        <secret>JBSWY3DPEHPK3PXP</secret>
    </token>
    <token>
        <issuer></issuer>
        <label>Google:test@gmail.com</label>
        <secret>JBSWY3DPEHPK3PXS</secret>
    </token>
    <token>
        <issuer>Simple</issuer>
        <label>simple</label>
        <secret></secret>
    </token>
</tokens>"""

    entries = parse_freeotp_xml(content)
    assert len(entries) == 2

    assert entries[0]["issuer"] == "GitHub"
    assert entries[0]["account_name"] == "user@github.com"
    assert entries[0]["secret"] == "JBSWY3DPEHPK3PXP"

    assert entries[1]["issuer"] == "Google"
    assert entries[1]["account_name"] == "test@gmail.com"
    assert entries[1]["secret"] == "JBSWY3DPEHPK3PXS"


def test_import_from_format_aegis(tmp_path: pathlib.Path) -> None:
    aegis_file = tmp_path / "aegis.json"
    aegis_file.write_text(
        '{"entries": [{"type": "totp", "issuer": "Test", "name": "test", "info": {"secret": "SECRET"}}]}'
    )

    entries = import_from_format("aegis", str(aegis_file))
    assert len(entries) == 1
    assert entries[0]["issuer"] == "Test"


def test_import_from_format_bitwarden(tmp_path: pathlib.Path) -> None:
    csv_file = tmp_path / "bitwarden.csv"
    csv_file.write_text("name,totp\nTest,SECRET")

    entries = import_from_format("bitwarden", str(csv_file))
    assert len(entries) == 1
    assert entries[0]["issuer"] == "Test"


def test_import_from_format_1password(tmp_path: pathlib.Path) -> None:
    csv_file = tmp_path / "1password.csv"
    csv_file.write_text("title,otp\nTest,SECRET")

    entries = import_from_format("1password", str(csv_file))
    assert len(entries) == 1
    assert entries[0]["issuer"] == "Test"


def test_import_from_format_otpauth() -> None:
    uri = "otpauth://totp/Test:test?secret=SECRET"
    entries = import_from_format("otpauth", uri)
    assert len(entries) == 1
    assert entries[0]["issuer"] == "Test"


def test_import_from_format_freeotp(tmp_path: pathlib.Path) -> None:
    xml_file = tmp_path / "freeotp.xml"
    xml_file.write_text(
        """<?xml version="1.0"?>
<tokens>
    <token>
        <issuer>Test</issuer>
        <label>test</label>
        <secret>SECRET</secret>
    </token>
</tokens>"""
    )

    entries = import_from_format("freeotp", str(xml_file))
    assert len(entries) == 1
    assert entries[0]["issuer"] == "Test"


def test_import_from_format_unsupported() -> None:
    with pytest.raises(ValueError, match="Unsupported format"):
        import_from_format("unsupported", "dummy")
