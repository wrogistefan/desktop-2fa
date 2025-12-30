import shutil
from pathlib import Path
from typing import Any

import pytest

from desktop_2fa.cli import commands, helpers


@pytest.fixture
def fake_vault_env(tmp_path: Path, monkeypatch: Any) -> Path:
    fake_vault = tmp_path / "vault"

    monkeypatch.setattr(
        "desktop_2fa.cli.helpers.get_vault_path",
        lambda: str(fake_vault),
    )
    monkeypatch.setattr(
        "desktop_2fa.cli.commands.get_vault_path",
        lambda: str(fake_vault),
    )

    # Upewniamy się, że katalog jest czysty
    if fake_vault.parent.exists():
        shutil.rmtree(fake_vault.parent)
    fake_vault.parent.mkdir(parents=True, exist_ok=True)

    return fake_vault


def test_list_entries_empty(fake_vault_env: Path, capsys: Any) -> None:
    commands.list_entries()
    out = capsys.readouterr().out.strip()
    assert out == "Vault is empty."


def test_add_entry_and_list(fake_vault_env: Path, capsys: Any) -> None:
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP")

    commands.list_entries()
    out = capsys.readouterr().out.strip().splitlines()

    assert out == ["Added entry: GitHub", "- GitHub (GitHub)"]

    vault = helpers.load_vault()
    assert len(vault.entries) == 1
    assert vault.entries[0].issuer == "GitHub"
    assert vault.entries[0].account_name == "GitHub"
    assert vault.entries[0].secret == "JBSWY3DPEHPK3PXP"


def test_generate_code(fake_vault_env: Path, capsys: Any) -> None:
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP")

    commands.generate_code("GitHub")
    out = capsys.readouterr().out.strip()

    lines = out.splitlines()
    assert lines[0] == "Added entry: GitHub"
    code = lines[1]
    assert len(code) == 6
    assert code.isdigit()


def test_generate_code_missing_entry_raises(fake_vault_env: Path) -> None:
    with pytest.raises(Exception):
        commands.generate_code("NonExisting")


def test_remove_entry(fake_vault_env: Path) -> None:
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP")
    commands.remove_entry("GitHub")

    vault = helpers.load_vault()
    assert len(vault.entries) == 0


def test_remove_entry_missing_raises(fake_vault_env: Path) -> None:
    with pytest.raises(Exception):
        commands.remove_entry("Nope")


def test_rename_entry(fake_vault_env: Path) -> None:
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP")
    commands.rename_entry("GitHub", "NewGitHub")

    vault = helpers.load_vault()
    assert len(vault.entries) == 1
    entry = vault.entries[0]
    assert entry.account_name == "NewGitHub"
    assert entry.issuer == "NewGitHub"


def test_rename_entry_missing_raises(fake_vault_env: Path) -> None:
    with pytest.raises(Exception):
        commands.rename_entry("Old", "New")


def test_export_vault(fake_vault_env: Path, tmp_path: Path, capsys: Any) -> None:
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP")

    export_path = tmp_path / "export.json"
    commands.export_vault(str(export_path))

    assert export_path.exists()
    assert export_path.stat().st_size > 0

    out = capsys.readouterr().out
    assert "Vault exported to" in out


def test_export_vault_missing_file(
    fake_vault_env: Path, tmp_path: Path, monkeypatch: Any, capsys: Any
) -> None:
    # sprawiamy, że get_vault_path wskazuje na nieistniejący plik
    fake_vault = tmp_path / "vault_missing"
    monkeypatch.setattr(
        "desktop_2fa.cli.helpers.get_vault_path",
        lambda: str(fake_vault),
    )

    commands.export_vault(str(tmp_path / "any.json"))
    out = capsys.readouterr().out
    assert "Vault does not exist." in out


def test_import_vault(
    fake_vault_env: Path, tmp_path: Path, capsys: Any, monkeypatch: Any
) -> None:
    # najpierw tworzymy "źródłowy" vault
    src_json = tmp_path / "src.json"
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP")
    commands.export_vault(str(src_json))

    # clear the vault
    vault = helpers.load_vault()
    vault.data.entries.clear()
    helpers.save_vault(vault)

    # import
    commands.import_vault(str(src_json))

    vault = helpers.load_vault()
    assert len(vault.entries) == 1
    assert vault.entries[0].issuer == "GitHub"
    assert vault.entries[0].secret == "JBSWY3DPEHPK3PXP"

    out = capsys.readouterr().out
    assert "Vault imported from" in out


def test_import_vault_missing_source(
    fake_vault_env: Path, tmp_path: Path, capsys: Any
) -> None:
    missing = tmp_path / "nope.json"
    commands.import_vault(str(missing))

    out = capsys.readouterr().out
    assert "Source file does not exist." in out


def test_backup_vault(fake_vault_env: Path, capsys: Any) -> None:
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP")

    vault_path = Path(helpers.get_vault_path())
    backup_path = vault_path.with_suffix(".backup.bin")

    commands.backup_vault()

    assert backup_path.exists()
    assert backup_path.stat().st_size > 0

    out = capsys.readouterr().out
    assert "Backup created:" in out


def test_backup_vault_missing(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    # brak pliku vault
    fake_vault = tmp_path / "no_vault_here"
    monkeypatch.setattr(
        "desktop_2fa.cli.helpers.get_vault_path",
        lambda: str(fake_vault),
    )

    commands.backup_vault()
    out = capsys.readouterr().out
    assert "Vault does not exist." in out
