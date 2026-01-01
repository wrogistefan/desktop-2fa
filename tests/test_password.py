from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from desktop_2fa.cli.helpers import get_password_from_cli
from desktop_2fa.cli.main import app


@pytest.fixture
def fake_ctx():
    """Create a fake typer context."""

    class FakeContext:
        def __init__(self):
            self.obj = {}

    return FakeContext()


def test_get_password_from_flag(fake_ctx):
    """Test getting password from --password flag."""
    fake_ctx.obj["password"] = "testpass"
    fake_ctx.obj["interactive"] = True
    assert get_password_from_cli(fake_ctx) == "testpass"


def test_get_password_from_file(fake_ctx, tmp_path):
    """Test getting password from --password-file flag."""
    password_file = tmp_path / "password.txt"
    password_file.write_text("filepass")
    fake_ctx.obj["password_file"] = str(password_file)
    fake_ctx.obj["interactive"] = True
    assert get_password_from_cli(fake_ctx) == "filepass"


def test_get_password_both_flags_error(fake_ctx):
    """Test error when both --password and --password-file are provided."""
    fake_ctx.obj["password"] = "test"
    fake_ctx.obj["password_file"] = "file"
    fake_ctx.obj["interactive"] = True
    from click.exceptions import Exit

    with pytest.raises(Exit):
        get_password_from_cli(fake_ctx)


def test_get_password_file_not_found(fake_ctx):
    """Test error when password file does not exist."""
    fake_ctx.obj["password_file"] = "/nonexistent/file"
    fake_ctx.obj["interactive"] = True
    from click.exceptions import Exit

    with pytest.raises(Exit):
        get_password_from_cli(fake_ctx)


def test_get_password_non_interactive_no_password(fake_ctx):
    """Test error in non-interactive mode when no password provided."""
    fake_ctx.obj["interactive"] = False
    from click.exceptions import Exit

    with pytest.raises(Exit):
        get_password_from_cli(fake_ctx)


def test_get_password_interactive_success(fake_ctx):
    """Test interactive password prompt with confirmation."""
    fake_ctx.obj["interactive"] = True
    with patch("typer.prompt") as mock_prompt:
        mock_prompt.side_effect = ["mypass", "mypass"]
        assert get_password_from_cli(fake_ctx) == "mypass"
        assert mock_prompt.call_count == 2


def test_get_password_interactive_mismatch_retry(fake_ctx):
    """Test interactive password prompt with mismatch and retry."""
    fake_ctx.obj["interactive"] = True
    with patch("typer.prompt") as mock_prompt, patch("builtins.print") as mock_print:
        mock_prompt.side_effect = ["pass1", "pass2", "pass3", "pass3"]
        assert get_password_from_cli(fake_ctx) == "pass3"
        assert mock_prompt.call_count == 4
        mock_print.assert_called_with("Passwords do not match. Please try again.")


# CLI integration tests using CliRunner

runner = CliRunner()


@pytest.fixture
def fake_vault_env(tmp_path, monkeypatch):
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


def test_cli_password_flag(fake_vault_env):
    """Test --password flag in CLI."""
    result = runner.invoke(
        app, ["--password", "testpass", "add", "GitHub", "JBSWY3DPEHPK3PXP"]
    )
    assert result.exit_code == 0
    assert "Added entry: GitHub" in result.output


def test_cli_password_file_flag(fake_vault_env, tmp_path):
    """Test --password-file flag in CLI."""
    password_file = tmp_path / "pass.txt"
    password_file.write_text("filepass")
    result = runner.invoke(
        app,
        ["--password-file", str(password_file), "add", "GitHub", "JBSWY3DPEHPK3PXP"],
    )
    assert result.exit_code == 0
    assert "Added entry: GitHub" in result.output


def test_cli_both_password_flags_error(fake_vault_env, tmp_path):
    """Test error when both --password and --password-file are provided."""
    password_file = tmp_path / "pass.txt"
    password_file.write_text("filepass")
    result = runner.invoke(
        app, ["--password", "test", "--password-file", str(password_file), "list"]
    )
    assert result.exit_code == 1
    assert "Error: Cannot specify both --password and --password-file" in result.output


def test_cli_non_interactive_no_password_error(fake_vault_env):
    """Test error in non-interactive mode without password."""
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


def test_cli_interactive_password_prompt(fake_vault_env):
    """Test interactive password prompt in CLI."""
    # Set environment variable to force interactive mode for testing
    import os

    original_env = os.environ.get("DESKTOP_2FA_FORCE_INTERACTIVE")
    os.environ["DESKTOP_2FA_FORCE_INTERACTIVE"] = "1"

    try:
        with patch("typer.prompt") as mock_prompt:
            mock_prompt.side_effect = ["interpass", "interpass"]
            result = runner.invoke(app, ["add", "GitHub", "JBSWY3DPEHPK3PXP"])
            assert (
                result.exit_code == 0
            ), f"Exit code was {result.exit_code}, output: {result.output}"
            assert "Added entry: GitHub" in result.output
            assert mock_prompt.call_count == 2
    finally:
        # Restore original environment
        if original_env is None:
            os.environ.pop("DESKTOP_2FA_FORCE_INTERACTIVE", None)
        else:
            os.environ["DESKTOP_2FA_FORCE_INTERACTIVE"] = original_env
