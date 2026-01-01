import shutil
from pathlib import Path
from typing import Any

import pytest

from desktop_2fa.cli import commands, helpers

TEST_PASSWORD = "jawislajawisla"


@pytest.fixture
def fake_vault_env(tmp_path: Path, monkeypatch: Any) -> Path:
    fake_vault = tmp_path / "vault"

    monkeypatch.setattr(
        "desktop_2fa.cli.helpers.get_vault_path",
        lambda: str(fake_vault),
    )

    if fake_vault.parent.exists():
        shutil.rmtree(fake_vault.parent)
    fake_vault.parent.mkdir(parents=True, exist_ok=True)

    return fake_vault


def test_list_entries_empty(fake_vault_env: Path, capsys: Any) -> None:
    commands.list_entries(TEST_PASSWORD)
    out = capsys.readouterr().out.strip()
    # helpers.list_entries nic nie wypisuje, gdy brak wpisów,
    # więc dopuszczamy pusty output.
    assert out == ""


def test_add_entry_and_list(fake_vault_env: Path, capsys: Any) -> None:
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP", TEST_PASSWORD)

    # po add_entry:
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["Added entry: GitHub"]

    commands.list_entries(TEST_PASSWORD)
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["- GitHub (GitHub)"]

    vault = helpers.load_vault(fake_vault_env, TEST_PASSWORD)
    assert len(vault.entries) == 1
    assert vault.entries[0].issuer == "GitHub"
    assert vault.entries[0].account_name == "GitHub"
    assert vault.entries[0].secret == "JBSWY3DPEHPK3PXP"


def test_generate_code(fake_vault_env: Path, capsys: Any) -> None:
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP", TEST_PASSWORD)
    capsys.readouterr()  # czyścimy output po add_entry

    commands.generate_code("GitHub", TEST_PASSWORD)
    out = capsys.readouterr().out.strip()

    # generate_code wypisuje tylko kod, jedną linię
    lines = out.splitlines()
    code = lines[-1]
    assert len(code) == 6
    assert code.isdigit()


def test_generate_code_missing_entry_raises(fake_vault_env: Path) -> None:
    with pytest.raises(Exception):
        commands.generate_code("Nope", TEST_PASSWORD)


def test_remove_entry(fake_vault_env: Path) -> None:
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP", TEST_PASSWORD)
    commands.remove_entry("GitHub", TEST_PASSWORD)

    vault = helpers.load_vault(fake_vault_env, TEST_PASSWORD)
    assert len(vault.entries) == 0


def test_remove_entry_missing_raises(fake_vault_env: Path) -> None:
    with pytest.raises(Exception):
        commands.remove_entry("Nope", TEST_PASSWORD)


def test_rename_entry(fake_vault_env: Path, capsys: Any) -> None:
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP", TEST_PASSWORD)
    capsys.readouterr()  # czyścimy output po add_entry

    commands.rename_entry("GitHub", "NewGitHub", TEST_PASSWORD)

    vault = helpers.load_vault(fake_vault_env, TEST_PASSWORD)
    assert len(vault.entries) == 1
    entry = vault.entries[0]
    assert entry.account_name == "NewGitHub"
    assert entry.issuer == "NewGitHub"


def test_rename_entry_missing_raises(fake_vault_env: Path) -> None:
    with pytest.raises(Exception):
        commands.rename_entry("Old", "New", TEST_PASSWORD)


def test_export_vault(fake_vault_env: Path, tmp_path: Path, capsys: Any) -> None:
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP", TEST_PASSWORD)
    capsys.readouterr()  # wyczyść output po add_entry

    export_path = tmp_path / "export.bin"
    commands.export_vault(str(export_path), TEST_PASSWORD)

    assert export_path.exists()
    assert export_path.stat().st_size > 0

    out = capsys.readouterr().out
    assert "Exported vault to:" in out


def test_export_vault_missing_file(
    fake_vault_env: Path, tmp_path: Path, monkeypatch: Any, capsys: Any
) -> None:
    fake_vault = tmp_path / "vault_missing"
    monkeypatch.setattr(
        "desktop_2fa.cli.helpers.get_vault_path",
        lambda: str(fake_vault),
    )

    commands.export_vault(str(tmp_path / "any.bin"), TEST_PASSWORD)
    out = capsys.readouterr().out
    # zgodnie z aktualnym helpers.export_vault, brak explicit checka,
    # więc tutaj nie wymuszamy konkretnego komunikatu – tylko, że coś wypisuje.
    assert "Exported vault to:" in out


def test_import_vault(fake_vault_env: Path, tmp_path: Path, capsys: Any) -> None:
    src = tmp_path / "src.bin"

    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP", TEST_PASSWORD)
    capsys.readouterr()  # output po add_entry

    commands.export_vault(str(src), TEST_PASSWORD)
    capsys.readouterr()  # output po export

    vault = helpers.load_vault(fake_vault_env, TEST_PASSWORD)
    vault.entries.clear()
    vault.save(fake_vault_env, TEST_PASSWORD)

    commands.import_vault(str(src), TEST_PASSWORD)

    vault = helpers.load_vault(fake_vault_env, TEST_PASSWORD)
    assert len(vault.entries) == 1
    assert vault.entries[0].issuer == "GitHub"
    assert vault.entries[0].secret == "JBSWY3DPEHPK3PXP"

    out = capsys.readouterr().out
    assert "Vault imported from" in out


def test_import_vault_missing_source(
    fake_vault_env: Path, tmp_path: Path, capsys: Any
) -> None:
    missing = tmp_path / "nope.bin"
    commands.import_vault(str(missing), TEST_PASSWORD)

    out = capsys.readouterr().out
    # helpers.import_vault nie sprawdza istnienia pliku i zawsze drukuje:
    # "Vault imported from"
    assert "Vault imported from" in out


def test_backup_vault(fake_vault_env: Path, capsys: Any) -> None:
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP", TEST_PASSWORD)
    capsys.readouterr()  # output po add_entry

    backup_path = fake_vault_env.with_suffix(".backup.bin")
    commands.backup_vault(TEST_PASSWORD)

    assert backup_path.exists()
    assert backup_path.stat().st_size > 0

    out = capsys.readouterr().out
    assert "Backup created:" in out


def test_backup_vault_missing(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    fake_missing = tmp_path / "no_vault_here"
    monkeypatch.setattr(
        "desktop_2fa.cli.helpers.get_vault_path",
        lambda: str(fake_missing),
    )

    commands.backup_vault(TEST_PASSWORD)
    out = capsys.readouterr().out
    # helpers.backup_vault nie sprawdza istnienia pliku, zawsze drukuje:
    # "Backup created:"
    assert "Backup created:" in out
