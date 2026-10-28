"""Shared Base32 boundaries use only synthetic keys and temporary vaults."""

import asyncio
import base64
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode

import pytest
import typer
from click import Command
from typer.testing import CliRunner

from desktop_2fa.cli import commands, helpers
from desktop_2fa.cli.main import app
from desktop_2fa.totp.generator import generate
from desktop_2fa.utils.base32 import InvalidSecret, decode_base32, normalize_base32
from desktop_2fa.vault import TotpEntry, Vault, VaultData

PASSWORD = "synthetic-base32-password"
VALID = ["MY======", "MY", "my======", "my", " m y = = = = = = "]
INVALID = [
    "",
    " ",
    "M",
    "MZX",
    "MZXW6Y",
    "MY=",
    "MY=======",
    "MY===A==",
    "MY======!",
    "JBSWY3DPEHPK3PXP=",
    "M1",
    "M0",
    "M!",
    "M\tY",
    "MY\n",
    "ＭＹ",
    "ſBSWY3DPEHPK3PXP",
    "ıBSWY3DPEHPK3PXP",
    "M\u00a0Y",
]


@pytest.mark.parametrize(
    "seed,encoded",
    [
        (b"f", "MY======"),
        (b"fo", "MZXQ===="),
        (b"foo", "MZXW6==="),
        (b"foob", "MZXW6YQ="),
        (b"fooba", "MZXW6YTB"),
    ],
)
def test_supported_padding_lengths(seed: bytes, encoded: str) -> None:
    assert decode_base32(encoded) == seed
    assert decode_base32(encoded.rstrip("=")) == seed
    assert normalize_base32(encoded.lower()) == encoded


@pytest.mark.parametrize("secret", VALID)
def test_accepted_input_is_consistent_across_boundaries(
    tmp_path: Path, secret: str
) -> None:
    assert decode_base32(secret) == b"f"
    assert normalize_base32(secret) == "MY======"
    assert helpers.validate_base32(secret)
    stored = TotpEntry(account_name="synthetic", secret=secret)
    assert stored.secret == secret  # Loading never canonicalizes stored text.
    assert generate(secret, timestamp=59) == generate("MY======", timestamp=59)
    uri = "otpauth://totp/Example:alice?" + urlencode({"secret": secret})
    assert helpers.parse_otpauth_url(uri)["secret"] == "MY======"
    vault = Vault()
    vault.add_entry("synthetic", "test", secret)
    assert vault.entries[0].secret == "MY======"
    path = tmp_path / "vault.bin"
    vault.save(path, PASSWORD)
    loaded = Vault.load(path, PASSWORD)
    assert decode_base32(loaded.entries[0].secret) == b"f"
    assert generate(loaded.entries[0].secret, timestamp=59) == generate(
        secret, timestamp=59
    )


@pytest.mark.parametrize("secret", INVALID)
def test_invalid_input_is_rejected_without_mutation(secret: str) -> None:
    assert not helpers.validate_base32(secret)
    with pytest.raises(InvalidSecret):
        decode_base32(secret)
    with pytest.raises(InvalidSecret):
        generate(secret, timestamp=59)
    vault = Vault()
    with pytest.raises(InvalidSecret):
        vault.add_entry("synthetic", "test", secret)
    assert vault.entries == []
    with pytest.raises(ValueError):
        helpers.parse_otpauth_url(
            "otpauth://totp/Example:alice?" + urlencode({"secret": secret})
        )
    if secret.strip(" ") and secret not in {"ſBSWY3DPEHPK3PXP", "ıBSWY3DPEHPK3PXP"}:
        with pytest.raises(ValueError):
            TotpEntry(secret=secret)


@pytest.mark.parametrize(
    "algorithm,seed,expected",
    [
        ("SHA1", b"12345678901234567890", "94287082"),
        ("SHA256", b"12345678901234567890123456789012", "46119246"),
        (
            "SHA512",
            b"1234567890123456789012345678901234567890123456789012345678901234",
            "90693936",
        ),
    ],
)
@pytest.mark.parametrize("variant", ["original", "lowercase", "unpadded", "spaces"])
def test_equivalent_encodings_preserve_rfc6238_codes(
    algorithm: str, seed: bytes, expected: str, variant: str
) -> None:
    secret = base64.b32encode(seed).decode()
    if variant == "lowercase":
        secret = secret.lower()
    elif variant == "unpadded":
        secret = secret.rstrip("=")
    elif variant == "spaces":
        secret = " ".join(secret)
    assert decode_base32(secret) == seed
    assert generate(secret, timestamp=59, digits=8, algorithm=algorithm) == expected


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("interactive", [False, True])
@pytest.mark.parametrize("secret", ["", " ", "MY=", "ſBSWY3DPEHPK3PXP"])
def test_add_rejects_before_vault_access(
    tmp_path: Path,
    existing: bool,
    interactive: bool,
    secret: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "vault.bin"
    if existing:
        Vault().save(path, PASSWORD)
    original = path.read_bytes() if existing else None
    ctx = typer.Context(Command("add"))
    ctx.obj = {"vault_path": path, "password": PASSWORD}

    def unexpected(*args: object, **kwargs: object) -> None:
        pytest.fail("Invalid secrets must fail before vault/password access")

    monkeypatch.setattr(helpers, "get_password_for_vault", unexpected)
    monkeypatch.setattr(commands, "_vault_exists", unexpected)
    operation = commands.add_entry_interactive if interactive else commands.add_entry
    with pytest.raises(typer.Exit) as error:
        operation("synthetic", "test", secret, ctx)
    assert error.value.exit_code == 6
    assert (path.read_bytes() if path.exists() else None) == original


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("interactive", [False, True])
def test_cli_manual_unpadded_secret_is_persisted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, existing: bool, interactive: bool
) -> None:
    path = tmp_path / "vault.bin"
    if existing:
        Vault().save(path, PASSWORD)
    if interactive:
        monkeypatch.setenv("DESKTOP_2FA_FORCE_INTERACTIVE", "1")
        args, user_input = [], "synthetic\ntest\nm y\n"
    else:
        monkeypatch.delenv("DESKTOP_2FA_FORCE_INTERACTIVE", raising=False)
        args, user_input = ["synthetic", "test", "m y"], ""
    result = CliRunner().invoke(
        app,
        ["--vault", str(path), "--password", PASSWORD, "add", *args],
        input=user_input,
    )
    assert result.exit_code == 0, result.output
    entry = Vault.load(path, PASSWORD).entries[0]
    assert entry.secret == "MY======"
    assert generate(entry.secret, timestamp=59) == generate("MY======", timestamp=59)


def test_helper_rejects_empty_before_loading(tmp_path: Path) -> None:
    with pytest.raises(InvalidSecret):
        helpers.add_entry(tmp_path / "missing", "test", "synthetic", "", PASSWORD)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("legacy_secret", ["", "ſBSWY3DPEHPK3PXP", "ıBSWY3DPEHPK3PXP"])
def test_legacy_invalid_entry_can_be_listed_and_repaired(
    tmp_path: Path, legacy_secret: str
) -> None:
    path = tmp_path / "legacy.bin"
    healthy = TotpEntry(
        account_name="healthy",
        secret="my======",
        digits=8,
        algorithm="SHA256",
        period=45,
    )
    vault = Vault(
        VaultData(
            entries=[
                TotpEntry(account_name="legacy-empty", secret=legacy_secret),
                healthy,
            ]
        )
    )
    vault.save(path, PASSWORD)
    original = path.read_bytes()
    runner = CliRunner()
    prefix = ["--vault", str(path), "--password", PASSWORD]
    listed = runner.invoke(app, prefix + ["list", "--indices"])
    assert listed.exit_code == 0, listed.output
    assert "legacy-empty" in listed.output
    assert path.read_bytes() == original
    assert Vault.load(path, PASSWORD).entries[0].secret == legacy_secret
    failed = runner.invoke(app, prefix + ["code", "legacy-empty", "--json"])
    assert failed.exit_code == 6, failed.output
    assert json.loads(failed.output)["error"] == "invalid_secret"
    assert "password" not in failed.output
    assert path.read_bytes() == original
    assert runner.invoke(app, prefix + ["code", "healthy", "--raw"]).exit_code == 0
    assert (
        runner.invoke(app, prefix + ["add", "replacement", "test", "MY"]).exit_code == 0
    )
    assert runner.invoke(app, prefix + ["remove", "legacy-empty"]).exit_code == 0
    loaded = Vault.load(path, PASSWORD)
    assert loaded.entries[0].model_dump() == healthy.model_dump()
    assert loaded.entries[1].secret == "MY======"


@pytest.mark.parametrize("action", ["generate", "copy"])
def test_ui_reports_legacy_empty_key_without_generating_or_copying(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, action: str
) -> None:
    from desktop_2fa.ui_textual.app import D2FAApp

    path = tmp_path / "legacy.bin"
    Vault(VaultData(entries=[TotpEntry(account_name="legacy", secret="")])).save(
        path, PASSWORD
    )
    ui = D2FAApp(str(path), PASSWORD)
    messages: list[str] = []
    widgets = {
        "#accounts": SimpleNamespace(index=0),
        "#output": SimpleNamespace(update=messages.append),
    }
    monkeypatch.setattr(ui, "query_one", lambda selector, *args: widgets[selector])

    def unexpected_copy(code: str) -> None:
        pytest.fail("Invalid legacy keys must not produce clipboard data")

    monkeypatch.setattr(ui, "_copy_to_clipboard", unexpected_copy)
    event = SimpleNamespace(button=SimpleNamespace(id=action))
    asyncio.run(ui.on_button_pressed(event))  # type: ignore[arg-type]
    assert messages == ["Invalid TOTP secret. Repair this entry using the CLI."]
