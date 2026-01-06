import re
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
    # Non-interactive list now prints all required messages when creating vault
    assert "No vault found." in result.output
    assert "A new encrypted vault will be created." in result.output
    assert f"Vault created at {fake_vault_env_cli}" in result.output


def test_cli_add_and_list(fake_vault_env_cli: Path) -> None:
    result = runner.invoke(
        app,
        ["--password", TEST_PASSWORD, "add", "GitHub", "GitHub", "JBSWY3DPEHPK3PXP"],
    )
    assert result.exit_code == 0
    assert "Entry added: GitHub" in result.output

    result = runner.invoke(app, ["--password", TEST_PASSWORD, "list"])
    assert result.exit_code == 0
    assert "- GitHub (GitHub)" in result.output


def test_cli_code(fake_vault_env_cli: Path) -> None:
    runner.invoke(
        app,
        ["--password", TEST_PASSWORD, "add", "GitHub", "GitHub", "JBSWY3DPEHPK3PXP"],
    )
    result = runner.invoke(app, ["--password", TEST_PASSWORD, "code", "GitHub"])
    assert result.exit_code == 0
    code = result.output.strip()
    assert len(code) == 6
    assert code.isdigit()


def test_cli_remove(fake_vault_env_cli: Path) -> None:
    runner.invoke(
        app,
        ["--password", TEST_PASSWORD, "add", "GitHub", "GitHub", "JBSWY3DPEHPK3PXP"],
    )
    result = runner.invoke(app, ["--password", TEST_PASSWORD, "remove", "GitHub"])
    assert result.exit_code == 0
    assert "Removed entry: GitHub" in result.output


def test_cli_rename(fake_vault_env_cli: Path) -> None:
    runner.invoke(
        app,
        ["--password", TEST_PASSWORD, "add", "GitHub", "GitHub", "JBSWY3DPEHPK3PXP"],
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
        ["--password", TEST_PASSWORD, "add", "GitHub", "GitHub", "JBSWY3DPEHPK3PXP"],
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
        ["--password", TEST_PASSWORD, "add", "GitHub", "GitHub", "JBSWY3DPEHPK3PXP"],
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
        ["--password", TEST_PASSWORD, "add", "GitHub", "GitHub", "JBSWY3DPEHPK3PXP"],
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


def test_cli_add_missing_arguments(fake_vault_env_cli: Path) -> None:
    result = runner.invoke(app, ["--password", TEST_PASSWORD, "add"])
    assert result.exit_code == 1
    assert "Missing arguments: NAME, ISSUER and SECRET are required" in result.output
    assert "Usage: d2fa add NAME ISSUER SECRET" in result.output
    assert "Example: d2fa add GitHub GitHub ABCDEFGHIJKL1234" in result.output


def test_cli_add_missing_issuer(fake_vault_env_cli: Path) -> None:
    result = runner.invoke(
        app, ["--password", TEST_PASSWORD, "add", "Test", "", "JBSWY3DPEHPK3PXP"]
    )
    assert result.exit_code == 0  # Empty issuer is accepted
    assert "Entry added:" in result.output


def test_cli_add_missing_secret(fake_vault_env_cli: Path) -> None:
    result = runner.invoke(
        app, ["--password", TEST_PASSWORD, "add", "GitHub", "GitHub", ""]
    )
    assert result.exit_code == 0  # Empty secret is accepted
    assert "Entry added:" in result.output


def test_cli_init_vault_new(fake_vault_env_cli: Path) -> None:
    result = runner.invoke(app, ["--password", TEST_PASSWORD, "init-vault"])
    assert result.exit_code == 0
    assert f"Vault created at {fake_vault_env_cli}" in result.output
    assert fake_vault_env_cli.exists()


def test_cli_init_vault_existing_no_force(fake_vault_env_cli: Path) -> None:
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env_cli, TEST_PASSWORD)

    result = runner.invoke(app, ["--password", TEST_PASSWORD, "init-vault"])
    assert result.exit_code == 0
    assert "Vault already exists." in result.output
    assert "Use --force to overwrite." in result.output


def test_cli_init_vault_existing_with_force(fake_vault_env_cli: Path) -> None:
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env_cli, TEST_PASSWORD)

    result = runner.invoke(app, ["--password", TEST_PASSWORD, "init-vault", "--force"])
    assert result.exit_code == 0
    assert "Existing vault will be overwritten." in result.output
    assert f"Vault created at {fake_vault_env_cli}" in result.output


def test_cli_is_interactive_tty_detection(monkeypatch: Any) -> None:
    # Mock sys.stdin.isatty and sys.stdout.isatty to return True
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    from desktop_2fa.cli.main import is_interactive

    assert is_interactive() is True


def test_cli_is_interactive_non_tty(monkeypatch: Any) -> None:
    # Mock sys.stdin.isatty and sys.stdout.isatty to return False
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)

    from desktop_2fa.cli.main import is_interactive

    assert is_interactive() is False


def test_cli_is_interactive_force_environment(monkeypatch: Any) -> None:
    monkeypatch.setenv("DESKTOP_2FA_FORCE_INTERACTIVE", "1")

    from desktop_2fa.cli.main import is_interactive

    assert is_interactive() is True


def test_cli_interactive_empty_input(
    fake_vault_env_cli: Path, monkeypatch: Any
) -> None:

    # Mock typer.prompt to return empty string
    def mock_prompt(*args: Any, **kwargs: Any) -> str:
        return ""

    monkeypatch.setattr("typer.prompt", mock_prompt)

    # This should handle empty input gracefully
    result = runner.invoke(
        app,
        ["--password", TEST_PASSWORD, "add", "GitHub", "GitHub", "JBSWY3DPEHPK3PXP"],
    )
    assert result.exit_code == 0  # Should not crash


def test_cli_interactive_whitespace_input(
    fake_vault_env_cli: Path, monkeypatch: Any
) -> None:

    # Mock typer.prompt to return whitespace
    def mock_prompt(*args: Any, **kwargs: Any) -> str:
        return "   "

    monkeypatch.setattr("typer.prompt", mock_prompt)

    # This should handle whitespace input gracefully
    result = runner.invoke(
        app,
        ["--password", TEST_PASSWORD, "add", "GitHub", "GitHub", "JBSWY3DPEHPK3PXP"],
    )
    assert result.exit_code == 0  # Should not crash


def test_cli_add_interactive_prompts(
    fake_vault_env_cli: Path, monkeypatch: Any
) -> None:
    # Force interactive mode
    monkeypatch.setenv("DESKTOP_2FA_FORCE_INTERACTIVE", "1")

    # Mock typer.prompt to return values for name, issuer and secret
    responses = ["TestName", "TestIssuer", "JBSWY3DPEHPK3PXP"]
    monkeypatch.setattr("typer.prompt", lambda text, hide_input=False: responses.pop(0))

    result = runner.invoke(app, ["--password", TEST_PASSWORD, "add"])
    assert result.exit_code == 0
    assert "Entry added: TestName" in result.output


def test_no_rich_markup_in_prompts() -> None:
    # Patterns to search for
    forbidden_patterns = [
        r"\[cyan\]",
        r"\[red\]",
        r"\[green\]",
        r"\[yellow\]",
        r"\[magenta\]",
        r"\[blue\]",
        r"\[white\]",
        r"\[black\]",
    ]

    # Files to check
    src_dir = Path(__file__).parent.parent / "src"
    py_files = list(src_dir.rglob("*.py"))

    violations = []
    for file_path in py_files:
        try:
            content = file_path.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    violations.append(
                        f"{file_path}: {pattern} found {len(matches)} times"
                    )
        except Exception as e:
            violations.append(f"Error reading {file_path}: {e}")

    if violations:
        pytest.fail("Found Rich markup in prompts:\n" + "\n".join(violations))
