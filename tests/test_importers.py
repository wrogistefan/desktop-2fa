"""Synthetic provider-format fixtures, independent RFC codes and explicit refusals."""

import copy
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from desktop_2fa.cli.importers import (
    ImportFormatError,
    import_from_format,
    parse_1password_csv,
    parse_aegis_json,
    parse_bitwarden_csv,
    parse_freeotp_xml,
    parse_otpauth_uri,
)
from desktop_2fa.cli.main import app
from desktop_2fa.totp.generator import generate
from desktop_2fa.vault import Vault, VaultData

FIXTURES = Path(__file__).parent / "fixtures" / "imports"
SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"


def read_fixture(name: str) -> str:
    with (FIXTURES / name).open(encoding="utf-8", newline="") as stream:
        return stream.read()


def code(entry, timestamp):
    return generate(
        entry.secret,
        timestamp=timestamp,
        digits=entry.digits,
        algorithm=entry.algorithm,
        period=entry.period,
    )


@pytest.mark.parametrize(
    "format_name,filename,timestamp,expected",
    [
        ("aegis", "aegis_plain.json", 59, "46119246"),
        ("bitwarden", "bitwarden.csv", 60, "0693936"),
        ("1password", "onepassword_legacy.csv", 59, "46119246"),
        ("freeotp", "freeotp_legacy.xml", 59, "287082"),
    ],
)
def test_fixture_codes_and_encrypted_roundtrip(
    tmp_path, format_name, filename, timestamp, expected
):
    entries = import_from_format(format_name, str(FIXTURES / filename))
    vault = Vault(VaultData.model_validate({"entries": entries}))
    # RFC 6238 Appendix B counter-1 outputs (including supported truncation).
    assert code(vault.entries[0], timestamp) == expected
    before = vault.data.model_dump()
    path = tmp_path / "roundtrip.bin"
    vault.save(path, "synthetic-import-password", overwrite=False)
    loaded = Vault.load(path, "synthetic-import-password")
    assert loaded.data.model_dump() == before
    assert code(loaded.entries[0], timestamp) == expected
    assert loaded.entries[0].issuer == "Żółw"
    assert loaded.entries[0].account_name == "konto@example.invalid"


def test_bitwarden_preserves_csv_multiline_identity_and_skips_only_absent_tokens():
    entries = parse_bitwarden_csv(read_fixture("bitwarden.csv"))
    assert len(entries) == 2
    assert entries[0]["algorithm"] == "SHA512"
    assert entries[0]["digits"] == 7
    assert entries[0]["period"] == 60
    assert entries[1]["issuer"] == "CSV, multiline\r\nŻółw"
    assert entries[1]["account_name"] == "raw@example.invalid\r\nsecond"
    assert entries[1]["secret"] == SECRET


@pytest.mark.parametrize("version", [1, 2, 3])
def test_aegis_database_versions_with_known_totp_shape(version):
    data = json.loads(read_fixture("aegis_plain.json"))
    data["db"]["version"] = version
    entries = parse_aegis_json(json.dumps(data))
    assert len(entries) == 2
    assert (entries[0]["algorithm"], entries[0]["digits"], entries[0]["period"]) == (
        "SHA256",
        8,
        45,
    )


@pytest.mark.parametrize(
    "change", ["encrypted", "header", "envelope", "database", "old-shape", "empty"]
)
def test_aegis_unsupported_envelopes_are_explicit(change):
    data = json.loads(read_fixture("aegis_plain.json"))
    if change == "encrypted":
        data["db"] = "synthetic-private-ciphertext"
    elif change == "header":
        data["header"]["params"] = {"nonce": "synthetic-private-value"}
    elif change == "envelope":
        data["version"] = 999
    elif change == "database":
        data["db"]["version"] = 999
    elif change == "old-shape":
        data = {"entries": data["db"]["entries"]}
    else:
        data["db"]["entries"] = []
    with pytest.raises(ImportFormatError) as error:
        parse_aegis_json(json.dumps(data))
    assert "synthetic-private" not in str(error.value)


@pytest.mark.parametrize(
    "change",
    [
        "hotp",
        "steam",
        "empty-secret",
        "missing-algo",
        "old-algorithm",
        "digits",
        "period",
        "unknown-parameter",
    ],
)
def test_aegis_bad_record_aborts_all_records(change):
    data = json.loads(read_fixture("aegis_plain.json"))
    bad = copy.deepcopy(data["db"]["entries"][0])
    if change in {"hotp", "steam"}:
        bad["type"] = change
    elif change == "empty-secret":
        bad["info"]["secret"] = ""
    elif change in {"missing-algo", "old-algorithm"}:
        bad["info"].pop("algo")
        if change == "old-algorithm":
            bad["info"]["algorithm"] = "SHA256"
    elif change == "digits":
        bad["info"]["digits"] = 9
    elif change == "period":
        bad["info"]["period"] = 0
    else:
        bad["info"]["counter"] = 42
    data["db"]["entries"].append(bad)
    with pytest.raises(ImportFormatError):
        parse_aegis_json(json.dumps(data))


@pytest.mark.parametrize(
    "text", ["{", "[]", "null", '{"version":true}', '{"version":1,"db":{}}']
)
def test_malformed_aegis(text):
    with pytest.raises(ImportFormatError):
        parse_aegis_json(text)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "name,totp\nwrong,synthetic-private-value",
        "name,login_totp\nx",
        "name,login_totp\nx,too,many",
        "name,login_totp,login_totp\nx,x,x",
        'name,login_totp\n"unterminated',
        "name,login_totp\nwithout-token,",
        f"type,name,login_totp\nnote,x,{SECRET}",
        f"name,login_totp\ngood,{SECRET}\nbad,synthetic-private-value",
    ],
)
def test_bad_csv_never_returns_fake_or_partial_success(text):
    with pytest.raises(ImportFormatError) as error:
        parse_bitwarden_csv(text)
    assert "synthetic-private-value" not in str(error.value)


@pytest.mark.parametrize(
    "uri",
    [
        "https://example.invalid/synthetic-private-value",
        "otpauth://hotp/test?secret=synthetic-private-value&counter=1",
        "otpauth://totp/test",
        f"otpauth://totp/test?secret={SECRET}&digits=9",
        f"otpauth://totp/test?secret={SECRET}&period=0",
        f"otpauth://totp/test?secret={SECRET}&algorithm=MD5",
        f"otpauth://totp/test?secret={SECRET}&secret={SECRET}",
    ],
)
def test_uri_errors_are_fixed_and_do_not_echo_input(uri):
    with pytest.raises(
        ImportFormatError, match="Invalid TOTP provisioning URI"
    ) as error:
        parse_otpauth_uri(uri)
    assert "synthetic-private-value" not in str(error.value)
    assert SECRET not in str(error.value)


def test_uri_dispatch_uses_shared_identity_and_normalization():
    entries = import_from_format(
        "otpauth", f"otpauth://totp/user%40example.invalid?secret={SECRET.lower()}"
    )
    assert entries[0]["account_name"] == "user@example.invalid"
    assert entries[0]["issuer"] == "user@example.invalid"
    assert entries[0]["secret"] == SECRET


def test_legacy_1password_otp_column_and_unsupported_native_projection():
    assert parse_1password_csv(f"title,otp\nlegacy,{SECRET}")[0]["secret"] == SECRET
    with pytest.raises(ImportFormatError):
        parse_1password_csv(read_fixture("onepassword_native_subset.csv"))
    with pytest.raises(ImportFormatError):
        parse_1password_csv(f"title,otp,one-time password\nx,{SECRET},{SECRET}")


@pytest.mark.parametrize(
    "text",
    [
        "<map><string name='tokenOrder'>[]</string></map>",
        "<tokens/>",
        "<!DOCTYPE tokens [<!ENTITY x 'synthetic-private-value'>]><tokens/>",
        "<tokens><token><secret>synthetic-private-value</secret></token></tokens>",
        f"<tokens><token><secret>{SECRET}</secret><period>45</period></token></tokens>",
        f"<tokens><token><secret>{SECRET}</secret><secret>{SECRET}</secret></token></tokens>",
        f"<tokens><token><secret>{SECRET}<nested/></secret></token></tokens>",
        "<broken",
    ],
)
def test_unsupported_or_malformed_xml_is_explicit(text):
    with pytest.raises(ImportFormatError) as error:
        parse_freeotp_xml(text)
    assert "synthetic-private-value" not in str(error.value)


def test_native_freeotp_backup_is_not_claimed_as_supported():
    with pytest.raises(ImportFormatError, match="native backups are not supported"):
        parse_freeotp_xml(read_fixture("freeotp_native.xml"))


def test_utf8_bom_multiline_and_invalid_encoding(tmp_path):
    source = tmp_path / "export.csv"
    source.write_bytes(b"\xef\xbb\xbf" + (FIXTURES / "bitwarden.csv").read_bytes())
    entries = import_from_format("BITWARDEN", str(source))
    assert entries[1]["account_name"] == "raw@example.invalid\r\nsecond"
    source.write_bytes(b"\xffsynthetic-private-value")
    with pytest.raises(ImportFormatError, match="UTF-8"):
        import_from_format("bitwarden", str(source))


def test_unsupported_format_does_not_open_source():
    with pytest.raises(ImportFormatError, match="Unsupported format"):
        import_from_format("unknown", "not-an-existing-file")


def test_cli_import_remains_encrypted_vault_only(tmp_path):
    source = tmp_path / "aegis.json"
    before = (FIXTURES / "aegis_plain.json").read_bytes()
    source.write_bytes(before)
    destination = tmp_path / "selected.bin"
    result = CliRunner().invoke(
        app,
        [
            "--vault",
            str(destination),
            "--password",
            "synthetic-password",
            "import",
            str(source),
        ],
    )
    assert result.exit_code == 1, result.output
    assert not destination.exists()
    assert source.read_bytes() == before
