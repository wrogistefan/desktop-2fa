from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from desktop_2fa.cli.main import app

runner = CliRunner()


def write_vault(tmp_path: Path, entries: list[dict[str, str]]) -> Path:
    """Helper: create a vault.json file in a temp directory."""
    vault_path = tmp_path / "vault.json"
    data = {"entries": entries}
    vault_path.write_text(json.dumps(data))
    return vault_path


def test_list_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    write_vault(tmp_path, [])

    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "Vault is empty" in result.stdout


def test_add_and_list(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    write_vault(tmp_path, [])

    result_add = runner.invoke(app, ["add", "github", "JBSWY3DPEHPK3PXP"])
    assert result_add.exit_code == 0
    assert "Added entry: github" in result_add.stdout

    result_list = runner.invoke(app, ["list"])
    assert result_list.exit_code == 0
    assert "- github" in result_list.stdout


def test_code_generation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    write_vault(tmp_path, [{"issuer": "github", "secret": "JBSWY3DPEHPK3PXP"}])

    result = runner.invoke(app, ["code", "github"])
    assert result.exit_code == 0
    assert result.stdout.strip().isdigit()
    assert len(result.stdout.strip()) == 6


def test_remove_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    write_vault(tmp_path, [{"issuer": "github", "secret": "AAA"}])

    result = runner.invoke(app, ["remove", "github"])
    assert result.exit_code == 0
    assert "Removed entry: github" in result.stdout

    result_list = runner.invoke(app, ["list"])
    assert "Vault is empty" in result_list.stdout


def test_rename_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    write_vault(tmp_path, [{"issuer": "github", "secret": "AAA"}])

    result = runner.invoke(app, ["rename", "github", "git"])
    assert result.exit_code == 0
    assert "Renamed github → git" in result.stdout

    result_list = runner.invoke(app, ["list"])
    assert "- git" in result_list.stdout


def test_export_vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    write_vault(tmp_path, [{"issuer": "github", "secret": "AAA"}])

    export_path = tmp_path / "export.json"
    result = runner.invoke(app, ["export", str(export_path)])
    assert result.exit_code == 0
    assert export_path.exists()

    exported = json.loads(export_path.read_text())
    assert exported["entries"][0]["issuer"] == "github"


def test_import_vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    # initial vault
    write_vault(tmp_path, [{"issuer": "old", "secret": "111"}])

    # external file to import
    import_file = tmp_path / "import.json"
    import_file.write_text(
        json.dumps({"entries": [{"issuer": "new", "secret": "222"}]})
    )

    result = runner.invoke(app, ["import", str(import_file)])
    assert result.exit_code == 0
    assert "Vault imported" in result.stdout

    result_list = runner.invoke(app, ["list"])
    assert "- new" in result_list.stdout


def test_backup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    write_vault(tmp_path, [{"issuer": "github", "secret": "AAA"}])

    result = runner.invoke(app, ["backup"])
    assert result.exit_code == 0
    assert "vault-backup-" in result.stdout

    # check backup file exists
    backup_files = list(tmp_path.glob("vault-backup-*.json"))
    assert len(backup_files) == 1
