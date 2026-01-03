import shutil
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from desktop_2fa.cli.helpers import load_vault, save_vault
from desktop_2fa.cli.main import app

TEST_PASSWORD = "jawislajawisla"
runner = CliRunner()


@pytest.fixture
def fake_vault_env_cli(tmp_path: Path, monkeypatch: Any) -> Path:
    fake_vault = tmp_path / "vault"

    monkeypatch.setattr(
        "desktop_2fa.cli.helpers.get_vault_path",
        lambda: str(fake_vault),
    )

    if fake_vault.parent.exists():
        shutil.rmtree(fake_vault.parent)
    fake_vault.parent.mkdir(parents=True, exist_ok=True)

    return fake_vault


def test_cli_list_empty(fake_vault_env_cli: Path) -> None:
    result = runner.invoke(app, ["--password", TEST_PASSWORD, "list"])
    assert result.exit_code == 0
    # helpers.list_entries prints nothing when empty
    assert result.output.strip() == ""


def test_cli_add_and_list(fake_vault_env_cli: Path) -> None:
    result = runner.invoke(
        app,
        ["--password", TEST_PASSWORD, "add", "GitHub", "JBSWY3DPEHPK3PXP"],
    )
    assert result.exit_code == 0
    assert "Entry added: GitHub" in result.output

    result = runner.invoke(app, ["--password", TEST_PASSWORD, "list"])
    assert result.exit_code == 0
    assert "- GitHub (GitHub)" in result.output


def test_cli_code(fake_vault_env_cli: Path) -> None:
    runner.invoke(
        app,
        ["--password", TEST_PASSWORD, "add", "GitHub", "JBSWY3DPEHPK3PXP"],
    )
    result = runner.invoke(app, ["--password", TEST_PASSWORD, "code", "GitHub"])
    assert result.exit_code == 0
    code = result.output.strip()
    assert len(code) == 6
    assert code.isdigit()


def test_cli_remove(fake_vault_env_cli: Path) -> None:
    runner.invoke(
        app,
        ["--password", TEST_PASSWORD, "add", "GitHub", "JBSWY3DPEHPK3PXP"],
    )
    result = runner.invoke(app, ["--password", TEST_PASSWORD, "remove", "GitHub"])
    assert result.exit_code == 0
    assert "Removed entry: GitHub" in result.output


def test_cli_rename(fake_vault_env_cli: Path) -> None:
    runner.invoke(
        app,
        ["--password", TEST_PASSWORD, "add", "GitHub", "JBSWY3DPEHPK3PXP"],
    )
    result = runner.invoke(
        app,
        ["--password", TEST_PASSWORD, "rename", "GitHub", "NewGitHub"],
    )
    assert result.exit_code == 0
    assert "Renamed 'GitHub' → 'NewGitHub'" in result.output


def test_cli_export(fake_vault_env_cli: Path, tmp_path: Path) -> None:
    runner.invoke(
        app,
        ["--password", TEST_PASSWORD, "add", "GitHub", "JBSWY3DPEHPK3PXP"],
    )
    export_path = tmp_path / "export.json"
    result = runner.invoke(
        app,
        ["--password", TEST_PASSWORD, "export", str(export_path)],
    )
    assert result.exit_code == 0
    assert "Exported vault to:" in result.output
    assert export_path.exists()


def test_cli_import(fake_vault_env_cli: Path, tmp_path: Path) -> None:
    runner.invoke(
        app,
        ["--password", TEST_PASSWORD, "add", "GitHub", "JBSWY3DPEHPK3PXP"],
    )
    export_path = tmp_path / "export.json"
    runner.invoke(
        app,
        ["--password", TEST_PASSWORD, "export", str(export_path)],
    )

    # Use the fake vault path instead of the default vault path
    vault = load_vault(fake_vault_env_cli, TEST_PASSWORD)
    vault.entries.clear()
    save_vault(fake_vault_env_cli, vault, TEST_PASSWORD)

    result = runner.invoke(
        app,
        ["--password", TEST_PASSWORD, "import", "--force", str(export_path)],
    )
    assert result.exit_code == 0
    assert "Vault imported from" in result.output


def test_cli_backup(fake_vault_env_cli: Path) -> None:
    runner.invoke(
        app,
        ["--password", TEST_PASSWORD, "add", "GitHub", "JBSWY3DPEHPK3PXP"],
    )
    result = runner.invoke(app, ["--password", TEST_PASSWORD, "backup"])
    assert result.exit_code == 0
    assert "Backup created:" in result.output


def test_cli_version(fake_vault_env_cli: Path) -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "Desktop-2FA v" in result.output


def test_cli_version_no_args(fake_vault_env_cli: Path) -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Desktop-2FA v" in result.output
