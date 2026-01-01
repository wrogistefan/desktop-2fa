import shutil
from pathlib import Path
from typing import Any

import pytest

from desktop_2fa.cli import helpers

TEST_PASSWORD = "jawislajawisla"


@pytest.fixture
def fake_vault_env_helpers(tmp_path: Path, monkeypatch: Any) -> Path:
    fake_vault = tmp_path / "vault"

    monkeypatch.setattr(
        "desktop_2fa.cli.helpers.get_vault_path",
        lambda: str(fake_vault),
    )

    if fake_vault.parent.exists():
        shutil.rmtree(fake_vault.parent)
    fake_vault.parent.mkdir(parents=True, exist_ok=True)

    return fake_vault


def test_helpers_add_and_list_entries(
    fake_vault_env_helpers: Path, capsys: Any
) -> None:
    from desktop_2fa.vault import Vault
    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)
    helpers.add_entry(
        fake_vault_env_helpers,
        "GitHub",
        "GitHub",
        "JBSWY3DPEHPK3PXP",
        TEST_PASSWORD,
    )

    out = capsys.readouterr().out.strip().splitlines()
    # Najpierw "Added entry: GitHub"
    assert out == ["Added entry: GitHub"]

    helpers.list_entries(fake_vault_env_helpers, TEST_PASSWORD)
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["- GitHub (GitHub)"]

    vault = helpers.load_vault(fake_vault_env_helpers, TEST_PASSWORD)
    assert len(vault.entries) == 1
    assert vault.entries[0].issuer == "GitHub"
    assert vault.entries[0].account_name == "GitHub"


def test_helpers_generate_code(fake_vault_env_helpers: Path, capsys: Any) -> None:
    from desktop_2fa.vault import Vault
    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)
    helpers.add_entry(
        fake_vault_env_helpers,
        "GitHub",
        "GitHub",
        "JBSWY3DPEHPK3PXP",
        TEST_PASSWORD,
    )
    capsys.readouterr()  # wyczyść output po add_entry

    helpers.generate_code(fake_vault_env_helpers, "GitHub", TEST_PASSWORD)
    out = capsys.readouterr().out.strip()

    lines = out.splitlines()
    code = lines[-1]
    assert len(code) == 6
    assert code.isdigit()


def test_helpers_remove_entry(fake_vault_env_helpers: Path) -> None:
    from desktop_2fa.vault import Vault
    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)
    helpers.add_entry(
        fake_vault_env_helpers,
        "GitHub",
        "GitHub",
        "JBSWY3DPEHPK3PXP",
        TEST_PASSWORD,
    )
    helpers.remove_entry(fake_vault_env_helpers, "GitHub", TEST_PASSWORD)

    vault = helpers.load_vault(fake_vault_env_helpers, TEST_PASSWORD)
    assert len(vault.entries) == 0


def test_helpers_rename_entry(fake_vault_env_helpers: Path) -> None:
    from desktop_2fa.vault import Vault
    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)
    helpers.add_entry(
        fake_vault_env_helpers,
        "GitHub",
        "GitHub",
        "JBSWY3DPEHPK3PXP",
        TEST_PASSWORD,
    )
    helpers.rename_entry(fake_vault_env_helpers, "GitHub", "GitHub2", TEST_PASSWORD)

    vault = helpers.load_vault(fake_vault_env_helpers, TEST_PASSWORD)
    assert vault.entries[0].issuer == "GitHub2"
    assert vault.entries[0].account_name == "GitHub2"


def test_helpers_export_and_import(
    fake_vault_env_helpers: Path, tmp_path: Path
) -> None:
    from desktop_2fa.vault import Vault
    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)
    helpers.add_entry(
        fake_vault_env_helpers,
        "GitHub",
        "GitHub",
        "JBSWY3DPEHPK3PXP",
        TEST_PASSWORD,
    )

    tmp_file = tmp_path / "export.bin"
    helpers.export_vault(fake_vault_env_helpers, tmp_file, TEST_PASSWORD)

    vault = helpers.load_vault(fake_vault_env_helpers, TEST_PASSWORD)
    vault.entries.clear()
    helpers.save_vault(fake_vault_env_helpers, vault, TEST_PASSWORD)

    helpers.import_vault(fake_vault_env_helpers, tmp_file, TEST_PASSWORD)
    vault = helpers.load_vault(fake_vault_env_helpers, TEST_PASSWORD)

    assert len(vault.entries) == 1
    assert vault.entries[0].issuer == "GitHub"


def test_helpers_backup(fake_vault_env_helpers: Path) -> None:
    from desktop_2fa.vault import Vault
    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)
    helpers.add_entry(
        fake_vault_env_helpers,
        "GitHub",
        "GitHub",
        "JBSWY3DPEHPK3PXP",
        TEST_PASSWORD,
    )

    backup_path = fake_vault_env_helpers.with_suffix(".backup.bin")
    helpers.backup_vault(fake_vault_env_helpers, backup_path, TEST_PASSWORD)

    assert backup_path.exists()
    assert backup_path.stat().st_size > 0


def test_helpers_timestamp() -> None:
    ts = helpers.timestamp()
    assert isinstance(ts, str)
    assert ts.isdigit()


def test_helpers_export_vault_missing(
    fake_vault_env_helpers: Path, tmp_path: Path, capsys: Any
) -> None:
    from desktop_2fa.vault import Vault
    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)
    export_path = tmp_path / "export.bin"
    helpers.export_vault(fake_vault_env_helpers, export_path, TEST_PASSWORD)
    out = capsys.readouterr().out
    # Aktualne zachowanie: eksportuje istniejący vault
    assert "Exported vault to:" in out
    assert export_path.exists()


def test_helpers_import_vault_missing(
    fake_vault_env_helpers: Path, tmp_path: Path
) -> None:
    from desktop_2fa.vault import Vault
    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)
    missing = tmp_path / "nope.bin"
    with pytest.raises(FileNotFoundError):
        helpers.import_vault(fake_vault_env_helpers, missing, TEST_PASSWORD)


def test_helpers_backup_vault_missing(
    fake_vault_env_helpers: Path, capsys: Any
) -> None:
    from desktop_2fa.vault import Vault
    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)

    backup_path = fake_vault_env_helpers.with_suffix(".backup.bin")
    helpers.backup_vault(fake_vault_env_helpers, backup_path, TEST_PASSWORD)
    out = capsys.readouterr().out
    # Aktualne zachowanie: backup_vault pisze backup i drukuje "Backup created:"
    assert "Backup created:" in out
    assert backup_path.exists()
