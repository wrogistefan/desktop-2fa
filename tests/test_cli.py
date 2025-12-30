import shutil
import tempfile
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from desktop_2fa.cli import commands
from desktop_2fa.cli.helpers import get_vault_path, load_vault, save_vault
from desktop_2fa.cli.main import app


def setup_function(_: object) -> None:
    vault_path = Path(get_vault_path())
    vault_dir = vault_path.parent

    if vault_dir.exists():
        shutil.rmtree(vault_dir)


def test_add_and_list_entries() -> None:
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP")

    vault = load_vault()
    assert len(vault.entries) == 1
    assert vault.entries[0].issuer == "GitHub"
    assert vault.entries[0].account_name == "GitHub"


def test_generate_code() -> None:
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP")

    # Should not raise
    commands.generate_code("GitHub")


def test_remove_entry() -> None:
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP")
    commands.remove_entry("GitHub")

    vault = load_vault()
    assert len(vault.entries) == 0


def test_rename_entry() -> None:
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP")
    commands.rename_entry("GitHub", "GitHub2")

    vault = load_vault()
    assert vault.entries[0].issuer == "GitHub2"
    assert vault.entries[0].account_name == "GitHub2"


def test_export_and_import() -> None:
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP")

    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()

    commands.export_vault(str(tmp_path))

    # Reset vault
    setup_function(None)

    commands.import_vault(str(tmp_path))
    vault = load_vault()

    assert len(vault.entries) == 1
    assert vault.entries[0].issuer == "GitHub"


def test_backup() -> None:
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP")

    vault_path = Path(get_vault_path())
    backup_path = vault_path.with_suffix(".backup.bin")

    commands.backup_vault()

    assert backup_path.exists()
    assert backup_path.stat().st_size > 0


# CLI tests using typer

runner = CliRunner()


@pytest.fixture
def fake_vault_env_cli(tmp_path: Path, monkeypatch: Any) -> Path:
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


def test_cli_list_empty(fake_vault_env_cli: Path) -> None:
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "Vault is empty." in result.output


def test_cli_add_and_list(fake_vault_env_cli: Path) -> None:
    result = runner.invoke(app, ["add", "GitHub", "JBSWY3DPEHPK3PXP"])
    assert result.exit_code == 0
    assert "Added TOTP entry for GitHub" in result.output

    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "- GitHub (GitHub)" in result.output


def test_cli_code(fake_vault_env_cli: Path) -> None:
    runner.invoke(app, ["add", "GitHub", "JBSWY3DPEHPK3PXP"])
    result = runner.invoke(app, ["code", "GitHub"])
    assert result.exit_code == 0
    assert len(result.output.strip()) == 6
    assert result.output.strip().isdigit()


def test_cli_remove(fake_vault_env_cli: Path) -> None:
    runner.invoke(app, ["add", "GitHub", "JBSWY3DPEHPK3PXP"])
    result = runner.invoke(app, ["remove", "GitHub"])
    assert result.exit_code == 0
    assert "Removed entry: GitHub" in result.output


def test_cli_rename(fake_vault_env_cli: Path) -> None:
    runner.invoke(app, ["add", "GitHub", "JBSWY3DPEHPK3PXP"])
    result = runner.invoke(app, ["rename", "GitHub", "NewGitHub"])
    assert result.exit_code == 0
    assert "Renamed GitHub → NewGitHub" in result.output


def test_cli_export(fake_vault_env_cli: Path, tmp_path: Path) -> None:
    runner.invoke(app, ["add", "GitHub", "JBSWY3DPEHPK3PXP"])
    export_path = tmp_path / "export.json"
    result = runner.invoke(app, ["export", str(export_path)])
    assert result.exit_code == 0
    assert "Vault exported to" in result.output
    assert export_path.exists()


def test_cli_import(fake_vault_env_cli: Path, tmp_path: Path) -> None:
    # First export
    runner.invoke(app, ["add", "GitHub", "JBSWY3DPEHPK3PXP"])
    export_path = tmp_path / "export.json"
    runner.invoke(app, ["export", str(export_path)])

    # Clear vault
    vault = load_vault()
    vault.data.entries.clear()
    save_vault(vault)

    # Import
    result = runner.invoke(app, ["import", str(export_path)])
    assert result.exit_code == 0
    assert "Vault imported from" in result.output


def test_cli_backup(fake_vault_env_cli: Path) -> None:
    runner.invoke(app, ["add", "GitHub", "JBSWY3DPEHPK3PXP"])
    result = runner.invoke(app, ["backup"])
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


def test_cli_add_interactive(fake_vault_env_cli: Path) -> None:
    # Provide issuer and secret via input
    result = runner.invoke(app, ["add"], input="GitHub\nJBSWY3DPEHPK3PXP\ny\n")
    assert result.exit_code == 0
    assert "Service provider name" in result.output
    assert "TOTP secret:" in result.output
    assert "Added TOTP entry for GitHub" in result.output


def test_cli_add_interactive_confirm_no(fake_vault_env_cli: Path) -> None:
    result = runner.invoke(
        app, ["add"], input="GitHub\nJBSWY3DPEHPK3PXP\nn\nJBSWY3DPEHPK3PXP\ny\n"
    )
    assert result.exit_code == 0
    assert "Is this correct?" in result.output
    assert "Added TOTP entry for GitHub" in result.output


def test_cli_add_interactive_repetitive(fake_vault_env_cli: Path) -> None:
    repetitive_secret = "AAAA" * 10
    result = runner.invoke(app, ["add"], input=f"GitHub\n{repetitive_secret}\ny\ny\n")
    assert result.exit_code == 0
    assert "unusually long or repetitive" in result.output
    assert "Added TOTP entry for GitHub" in result.output


def test_cli_add_error(fake_vault_env_cli: Path, monkeypatch: Any) -> None:
    def mock_add_entry(*args: Any, **kwargs: Any) -> None:
        raise ValueError("test error")

    monkeypatch.setattr("desktop_2fa.cli.main.add_entry", mock_add_entry)
    result = runner.invoke(app, ["add", "GitHub", "JBSWY3DPEHPK3PXP"])
    assert result.exit_code == 0
    assert "Error: test error" in result.output


def test_cli_add_empty_secret_loop(fake_vault_env_cli: Path, monkeypatch: Any) -> None:
    prompts = iter(["GitHub", "", "JBSWY3DPEHPK3PXP"])
    confirms = iter(["y"])
    monkeypatch.setattr("typer.prompt", lambda text, **kwargs: next(prompts))
    monkeypatch.setattr("typer.confirm", lambda text, **kwargs: next(confirms))
    result = runner.invoke(app, ["add"])
    assert result.exit_code == 0
    assert "Secret cannot be empty" in result.output
    assert "Added TOTP entry for GitHub" in result.output


def test_cli_add_repetitive_no(fake_vault_env_cli: Path, monkeypatch: Any) -> None:
    prompts = iter(["GitHub", "AAAA" * 10, "JBSWY3DPEHPK3PXP"])
    confirms = iter(["y", False, "y"])
    monkeypatch.setattr("typer.prompt", lambda text, **kwargs: next(prompts))
    monkeypatch.setattr("typer.confirm", lambda text, **kwargs: next(confirms))
    result = runner.invoke(app, ["add"])
    assert result.exit_code == 0
    assert "Added TOTP entry for GitHub" in result.output
