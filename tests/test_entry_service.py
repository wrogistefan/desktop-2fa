"""Parity at the public helper and both command boundaries, using synthetic data."""

from pathlib import Path

import pytest
import typer
from click import Command

from desktop_2fa import entry_service
from desktop_2fa.cli import commands, helpers
from desktop_2fa.vault import Vault

PASSWORD = "synthetic-service-password"
URI = (
    "otpauth://totp/Example:alice?secret=JBSWY3DPEHPK3PXP"
    "&algorithm=SHA256&digits=8&period=60"
)


@pytest.mark.parametrize("flow", ["helper", "interactive", "command"])
def test_add_and_rename_preserve_shared_rules(
    flow: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "synthetic-vault"
    Vault().save(path, PASSWORD)
    ctx = typer.Context(Command("synthetic"), obj={"password": PASSWORD})
    monkeypatch.setattr(commands, "_path", lambda _: path)
    if flow == "helper":
        helpers.add_entry(path, URI, "ignored", "", PASSWORD)
    else:
        add = (
            commands.add_entry_interactive
            if flow == "interactive"
            else commands.add_entry
        )
        add("ignored", URI, "", ctx)
    output = capsys.readouterr().out
    assert "alice" in output
    assert "ignored" not in output
    before = Vault.load(path, PASSWORD).entries[0].model_dump()
    assert (before["account_name"], before["issuer"]) == ("alice", "Example")
    assert (before["algorithm"], before["digits"], before["period"]) == (
        "SHA256",
        8,
        60,
    )
    if flow == "helper":
        helpers.rename_entry(path, "alice", "renamed", PASSWORD)
    else:
        commands.rename_entry("alice", "renamed", ctx)
    loaded = Vault.load(path, PASSWORD)
    assert loaded.entries[0].model_dump() == {
        **before,
        "account_name": "renamed",
        "issuer": "renamed",
    }
    entry, code, remaining = entry_service.generate_code(
        loaded, "renamed", timestamp=119
    )
    assert entry is loaded.entries[0]
    assert len(code) == 8
    assert remaining == 1


@pytest.mark.parametrize("flow", ["helper", "interactive", "command"])
def test_invalid_provisioning_leaves_original_file_untouched(
    flow: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "synthetic-vault"
    original = b"synthetic-unreadable-vault-must-not-be-loaded-or-overwritten"
    path.write_bytes(original)
    ctx = typer.Context(Command("synthetic"), obj={"password": PASSWORD})
    monkeypatch.setattr(commands, "_path", lambda _: path)
    if flow == "helper":
        with pytest.raises(ValueError):
            helpers.add_entry(path, URI, "ignored", "conflicting-secret", PASSWORD)
    else:
        add = (
            commands.add_entry_interactive
            if flow == "interactive"
            else commands.add_entry
        )
        with pytest.raises(typer.Exit) as caught:
            add("ignored", URI, "conflicting-secret", ctx)
        assert caught.value.exit_code == 6
    assert path.read_bytes() == original
