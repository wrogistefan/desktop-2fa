"""Provisioning parameters must survive both add flows and persistence."""

import base64
from pathlib import Path
from urllib.parse import urlencode

import pytest
from typer.testing import CliRunner

from desktop_2fa.cli.helpers import parse_otpauth_url
from desktop_2fa.cli.main import app
from desktop_2fa.totp.generator import generate
from desktop_2fa.vault import Vault

PASSWORD = "synthetic-provisioning-password"
SECRET = "JBSWY3DPEHPK3PXP"


def uri(secret: str = SECRET, **parameters: str) -> str:
    return "otpauth://totp/Example:alice?" + urlencode({"secret": secret, **parameters})


@pytest.mark.parametrize("flow", ["legacy", "single-uri", "interactive"])
@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize(
    "algorithm,seed,expected",
    [
        ("SHA256", b"12345678901234567890123456789012", "46119246"),
        (
            "SHA512",
            b"1234567890123456789012345678901234567890123456789012345678901234",
            "90693936",
        ),
    ],
)
def test_uri_parameters_and_exact_code_survive_add(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    flow: str,
    existing: bool,
    algorithm: str,
    seed: bytes,
    expected: str,
) -> None:
    path = tmp_path / "selected-vault"
    if existing:
        Vault().save(path, PASSWORD)
    url = uri(
        base64.b32encode(seed).decode(), algorithm=algorithm, digits="8", period="60"
    )
    parsed = parse_otpauth_url(url)
    assert (
        generate(
            parsed["secret"],
            timestamp=119,
            digits=int(parsed["digits"]),
            period=int(parsed["period"]),
            algorithm=parsed["algorithm"],
        )
        == expected
    )
    if flow == "interactive":
        monkeypatch.setenv("DESKTOP_2FA_FORCE_INTERACTIVE", "1")
        args = []
        user_input = "ignored-name\n" + url + "\n"
    else:
        monkeypatch.delenv("DESKTOP_2FA_FORCE_INTERACTIVE", raising=False)
        args = [url] if flow == "single-uri" else ["ignored-name", url, ""]
        user_input = ""
    result = CliRunner().invoke(
        app,
        ["--vault", str(path), "--password", PASSWORD, "add", *args],
        input=user_input,
    )
    assert result.exit_code == 0, result.output
    assert "Secret:" not in result.output
    saved = Vault.load(path, PASSWORD).entries[0]
    assert (
        saved.account_name,
        saved.issuer,
        saved.algorithm,
        saved.digits,
        saved.period,
    ) == ("alice", "Example", algorithm, 8, 60)
    assert base64.b32decode(saved.secret) == seed
    assert (
        generate(
            saved.secret,
            timestamp=119,
            digits=saved.digits,
            period=saved.period,
            algorithm=saved.algorithm,
        )
        == expected
    )


@pytest.mark.parametrize(
    "url,issuer,label",
    [
        (
            f"otpauth://totp/ACME%20Co%3A%20alice%40example.invalid?secret={SECRET}&issuer=ACME%20Co",
            "ACME Co",
            "alice@example.invalid",
        ),
        (f"otpauth://totp/alice?secret={SECRET}&issuer=Example", "Example", "alice"),
        (f"otpauth://totp/:alice?secret={SECRET}&issuer=Example", "Example", "alice"),
        (f"otpauth://totp/Legacy?secret={SECRET}", "Legacy", "Legacy"),
    ],
)
def test_labels_issuer_and_defaults(url: str, issuer: str, label: str) -> None:
    parsed = parse_otpauth_url(url)
    assert (parsed["issuer"], parsed["label"]) == (issuer, label)
    assert (parsed["algorithm"], parsed["digits"], parsed["period"]) == ("SHA1", 6, 30)


INVALID = [
    uri(algorithm="MD5"),
    uri(algorithm=""),
    uri(digits="5"),
    uri(digits="6.0"),
    uri(period="0"),
    uri(period="-1"),
    uri(period="30.0"),
    uri(period=""),
    uri(issuer="Conflicting"),
    uri() + "&digits=6&digits=8",
    uri() + "&secret=" + SECRET,
    "otpauth://totp/Example:alice?issuer=Example",
    uri(secret=""),
    uri(secret="INVALID!"),
    uri() + "&counter=1",
    uri() + "#fragment",
    f"otpauth://totp/Example:alice:extra?secret={SECRET}",
    f"otpauth://totp/Bad%GG?secret={SECRET}",
]


@pytest.mark.parametrize("url", INVALID)
def test_invalid_uri_is_rejected(url: str) -> None:
    with pytest.raises(ValueError):
        parse_otpauth_url(url)


@pytest.mark.parametrize(
    "secret",
    [
        "INVALID!",
        "JBSWY3DP!HPK3PXP",
        "JBSWY3DP0HPK3PXP",
        "JBSWY3DP1HPK3PXP",
        "JBSWY3DP8HPK3PXP",
        "JBSWY3DP HPK3PXP",
        "JBSWY3DP\nHPK3PXP",
        "JBſWY3DPEHPK3PXP",
        "JBßWY3DPEHPK3PXP",
        "JBSWY3DP=HPK3PXP",
    ],
)
def test_non_base32_characters_are_rejected_without_echoing_secret(secret: str) -> None:
    with pytest.raises(ValueError, match="^Invalid Base32 TOTP secret$"):
        parse_otpauth_url(uri(secret=secret))


@pytest.mark.parametrize("secret", [SECRET, SECRET.lower(), "jBsWy3DpEhPk3PxP"])
def test_ascii_secret_case_preserves_decoded_bytes(secret: str) -> None:
    assert parse_otpauth_url(uri(secret=secret))["secret"] == SECRET


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("flow", ["single-uri", "interactive"])
@pytest.mark.parametrize(
    "url",
    [
        uri(algorithm="MD5"),
        uri(digits="5"),
        uri(period="0"),
        uri(secret=""),
        uri(issuer="Conflicting"),
        uri(secret="INVALID!"),
        uri(secret="JBſWY3DPEHPK3PXP"),
    ],
)
def test_invalid_uri_never_changes_vault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, existing: bool, flow: str, url: str
) -> None:
    path = tmp_path / "selected-directory" / "selected-vault"
    if existing:
        Vault().save(path, PASSWORD)
    before = path.read_bytes() if existing else None
    monkeypatch.setenv(
        "DESKTOP_2FA_FORCE_INTERACTIVE", "1" if flow == "interactive" else "0"
    )
    result = CliRunner().invoke(
        app,
        [
            "--vault",
            str(path),
            "--password",
            PASSWORD,
            "add",
            *([url] if flow == "single-uri" else []),
        ],
        input="ignored\n" + url + "\n",
    )
    assert result.exit_code == 6, result.output
    assert "Invalid otpauth URL" in result.output
    if flow == "single-uri":
        assert SECRET not in result.output
    assert (path.read_bytes() if path.exists() else None) == before
    if not existing:
        assert not path.parent.exists()


@pytest.mark.parametrize("arguments", [[uri(), "extra"], ["name", uri(), SECRET]])
def test_uri_with_contradictory_arguments_is_rejected(
    tmp_path: Path, arguments: list[str]
) -> None:
    path = tmp_path / "selected-vault"
    result = CliRunner().invoke(
        app, ["--vault", str(path), "--password", PASSWORD, "add", *arguments]
    )
    assert result.exit_code == 6
    assert not path.exists()


def test_default_uri_with_encoded_label_is_persisted(tmp_path: Path) -> None:
    path = tmp_path / "selected-vault"
    result = CliRunner().invoke(
        app,
        [
            "--vault",
            str(path),
            "--password",
            PASSWORD,
            "add",
            f"otpauth://totp/Example%3Aalice%40example.invalid?secret={SECRET}&issuer=Example",
        ],
    )
    assert result.exit_code == 0, result.output
    saved = Vault.load(path, PASSWORD).entries[0]
    assert (
        saved.account_name,
        saved.issuer,
        saved.secret,
        saved.algorithm,
        saved.digits,
        saved.period,
    ) == ("alice@example.invalid", "Example", SECRET, "SHA1", 6, 30)


def test_unpadded_uri_secret_and_algorithm_case() -> None:
    secret = base64.b32encode(b"12345678901234567890123456789012").decode()
    parsed = parse_otpauth_url(
        uri(secret.rstrip("="), algorithm="sha256", digits="7", period="45")
    )
    assert parsed["secret"] == secret
    assert (parsed["algorithm"], parsed["digits"], parsed["period"]) == (
        "SHA256",
        7,
        45,
    )


def test_manual_add_api_defaults_and_custom_parameters() -> None:
    vault = Vault()
    vault.add_entry("manual", "Example", SECRET)
    vault.add_entry(
        "custom", "Example", SECRET, algorithm="SHA512", digits=7, period=45
    )
    assert (
        vault.entries[0].algorithm,
        vault.entries[0].digits,
        vault.entries[0].period,
    ) == ("SHA1", 6, 30)
    assert (
        vault.entries[1].algorithm,
        vault.entries[1].digits,
        vault.entries[1].period,
    ) == ("SHA512", 7, 45)
