import pathlib
from typing import Any, Dict
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from desktop_2fa.cli.helpers import get_password_from_cli
from desktop_2fa.cli.main import app


@pytest.fixture
def fake_ctx() -> Any:

    class FakeContext:
        def __init__(self) -> None:
            self.obj: Dict[str, Any] = {}

    return FakeContext()


def test_get_password_from_flag(fake_ctx: Any) -> None:
    fake_ctx.obj["password"] = "testpass"
    fake_ctx.obj["interactive"] = True
    assert get_password_from_cli(fake_ctx) == "testpass"


def test_get_password_from_file(fake_ctx: Any, tmp_path: pathlib.Path) -> None:
    password_file = tmp_path / "password.txt"
    password_file.write_text("filepass")
    fake_ctx.obj["password_file"] = str(password_file)
    fake_ctx.obj["interactive"] = True
    assert get_password_from_cli(fake_ctx) == "filepass"


def test_get_password_both_flags_error(fake_ctx: Any) -> None:
    fake_ctx.obj["password"] = "test"
    fake_ctx.obj["password_file"] = "file"
    fake_ctx.obj["interactive"] = True
    from click.exceptions import Exit

    with pytest.raises(Exit):
        get_password_from_cli(fake_ctx)


def test_get_password_file_not_found(fake_ctx: Any) -> None:
    fake_ctx.obj["password_file"] = "/nonexistent/file"
    fake_ctx.obj["interactive"] = True
    from click.exceptions import Exit

    with pytest.raises(Exit):
        get_password_from_cli(fake_ctx)


def test_get_password_non_interactive_no_password(fake_ctx: Any) -> None:
    fake_ctx.obj["interactive"] = False
    from click.exceptions import Exit

    with pytest.raises(Exit):
        get_password_from_cli(fake_ctx)


def test_get_password_interactive_success(fake_ctx: Any) -> None:
    fake_ctx.obj["interactive"] = True
    with patch("getpass.getpass") as mock_getpass:
        mock_getpass.return_value = "mypass"
        assert get_password_from_cli(fake_ctx) == "mypass"
        assert mock_getpass.call_count == 1


def test_get_password_interactive_mismatch_retry(fake_ctx: Any) -> None:
    fake_ctx.obj["interactive"] = True
    with patch("getpass.getpass") as mock_getpass:
        mock_getpass.return_value = "pass1"
        assert get_password_from_cli(fake_ctx) == "pass1"
        assert mock_getpass.call_count == 1


# CLI integration tests using CliRunner

runner = CliRunner()


@pytest.fixture
def fake_vault_env(tmp_path: pathlib.Path, monkeypatch: Any) -> pathlib.Path:
    fake_vault = tmp_path / "vault"

    monkeypatch.setattr(
        "desktop_2fa.cli.helpers.get_vault_path",
        lambda: str(fake_vault),
    )

    # Ensure directory is clean
    if fake_vault.parent.exists():
        import shutil

        shutil.rmtree(fake_vault.parent)
    fake_vault.parent.mkdir(parents=True, exist_ok=True)

    return fake_vault


def test_cli_password_flag(fake_vault_env: pathlib.Path) -> None:
    result = runner.invoke(
        app, ["--password", "testpass", "add", "GitHub", "GitHub", "JBSWY3DPEHPK3PXP"]
    )
    assert result.exit_code == 0
    assert "Entry added: GitHub" in result.output


def test_cli_password_file_flag(
    fake_vault_env: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    password_file = tmp_path / "pass.txt"
    password_file.write_text("filepass")
    result = runner.invoke(
        app,
        [
            "--password-file",
            str(password_file),
            "add",
            "GitHub",
            "GitHub",
            "JBSWY3DPEHPK3PXP",
        ],
    )
    assert result.exit_code == 0
    assert "Entry added: GitHub" in result.output


def test_cli_both_password_flags_error(
    fake_vault_env: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    password_file = tmp_path / "pass.txt"
    password_file.write_text("filepass")
    result = runner.invoke(
        app, ["--password", "test", "--password-file", str(password_file), "list"]
    )
    assert result.exit_code == 1
    assert "Error: Cannot specify both --password and --password-file" in result.output


def test_cli_non_interactive_no_password_error(fake_vault_env: pathlib.Path) -> None:
    with (
        patch("sys.stdin.isatty", return_value=False),
        patch("sys.stdout.isatty", return_value=False),
    ):
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 1
        assert (
            "Error: Password not provided and not running in interactive mode"
            in result.output
        )


def test_cli_interactive_password_prompt(fake_vault_env: pathlib.Path) -> None:
    # Set environment variable to force interactive mode for testing
    import os

    original_env = os.environ.get("DESKTOP_2FA_FORCE_INTERACTIVE")
    os.environ["DESKTOP_2FA_FORCE_INTERACTIVE"] = "1"

    try:
        with patch("getpass.getpass") as mock_getpass:
            mock_getpass.return_value = "interpass"
            result = runner.invoke(app, ["add", "GitHub", "GitHub", "JBSWY3DPEHPK3PXP"])
            assert (
                result.exit_code == 0
            ), f"Exit code was {result.exit_code}, output: {result.output}"
            assert "Entry added: GitHub" in result.output
            assert mock_getpass.call_count == 2  # password + confirmation
    finally:
        # Restore original environment
        if original_env is None:
            os.environ.pop("DESKTOP_2FA_FORCE_INTERACTIVE", None)
        else:
            os.environ["DESKTOP_2FA_FORCE_INTERACTIVE"] = original_env
