"""Synthetic add credentials must not appear in prompts or operation diagnostics."""

import base64
from unittest.mock import Mock, call

import pytest
import typer
from typer.testing import CliRunner

from desktop_2fa.cli.main import app
from desktop_2fa.vault import Vault

PASSWORD = "synthetic-hidden-prompt-password"
SECRET = base64.b32encode(b"synthetic S10 hidden secret marker").decode()
INVALID_SECRET = "synthetic-S10-invalid-secret-marker!"


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("valid", [False, True])
def test_full_interactive_add_hides_secret(tmp_path, monkeypatch, existing, valid):
    path = tmp_path / "synthetic-vault.bin"
    if existing:
        Vault().save(path, PASSWORD)
    before = path.read_bytes() if existing else None
    monkeypatch.setattr("desktop_2fa.cli.main.is_interactive", lambda: True)
    prompt = Mock(wraps=typer.prompt)
    monkeypatch.setattr(typer, "prompt", prompt)
    secret = SECRET if valid else INVALID_SECRET
    result = CliRunner().invoke(
        app,
        ["--vault", str(path), "--password", PASSWORD, "add"],
        input=f"synthetic-account\nsynthetic-issuer\n{secret}\n",
    )
    assert result.exit_code == (0 if valid else 6), result.output
    assert prompt.call_args_list == [call(""), call(""), call("", hide_input=True)]
    assert "Name (unique identifier):" in result.stdout
    assert "Issuer:" in result.stdout
    assert "Secret:" in result.stdout
    assert "synthetic-account" in result.stdout
    assert "synthetic-issuer" in result.stdout
    for stream in (result.stdout, result.stderr):
        assert secret not in stream
        assert PASSWORD not in stream
    if valid:
        assert "Entry added: synthetic-account" in result.stdout
        saved = Vault.load(path, PASSWORD).entries[0]
        assert saved.account_name == "synthetic-account"
        assert saved.issuer == "synthetic-issuer"
        assert base64.b32decode(saved.secret) == base64.b32decode(SECRET)
    elif existing:
        assert path.read_bytes() == before
    else:
        assert not path.exists()


def test_partial_interactive_add_hides_only_missing_secret(tmp_path, monkeypatch):
    path = tmp_path / "synthetic-vault.bin"
    monkeypatch.setattr("desktop_2fa.cli.main.is_interactive", lambda: True)
    prompt = Mock(wraps=typer.prompt)
    monkeypatch.setattr(typer, "prompt", prompt)
    result = CliRunner().invoke(
        app,
        ["--vault", str(path), "--password", PASSWORD, "add", "account", "issuer"],
        input=SECRET + "\n",
    )
    assert result.exit_code == 0, result.output
    prompt.assert_called_once_with("", hide_input=True)
    assert SECRET not in result.stdout + result.stderr
    assert "Entry added: account" in result.stdout


@pytest.mark.parametrize("valid", [False, True])
@pytest.mark.parametrize("source", ["argument", "issuer-prompt"])
def test_uri_operation_messages_omit_credentials(tmp_path, monkeypatch, valid, source):
    path = tmp_path / "synthetic-vault.bin"
    monkeypatch.setattr("desktop_2fa.cli.main.is_interactive", lambda: True)
    secret = SECRET if valid else INVALID_SECRET
    uri = f"otpauth://totp/Example:account?secret={secret}&issuer=Example"
    if source == "issuer-prompt":
        # Inspect application messages separately from visible issuer input echo.
        # Pasting a URI into that visible prompt can expose it in a real terminal.
        prompt = Mock(side_effect=["ignored-name", uri])
        args = []
    else:
        prompt = Mock(side_effect=AssertionError("positional URI must not prompt"))
        args = [uri]
    monkeypatch.setattr(typer, "prompt", prompt)
    result = CliRunner().invoke(
        app, ["--vault", str(path), "--password", PASSWORD, "add", *args]
    )
    assert result.exit_code == (0 if valid else 6), result.output
    assert "Secret:" not in result.output
    assert uri not in result.stdout + result.stderr
    assert secret not in result.stdout + result.stderr
    if source == "issuer-prompt":
        assert prompt.call_args_list == [call(""), call("")]
    else:
        prompt.assert_not_called()
    if valid:
        assert "Entry added: account" in result.stdout
    else:
        assert "Invalid otpauth URL" in result.stderr
        assert not path.exists()


@pytest.mark.parametrize("source", ["argument", "issuer-prompt"])
def test_malformed_uri_parser_error_never_echoes_input(tmp_path, monkeypatch, source):
    path = tmp_path / "synthetic-vault.bin"
    monkeypatch.setattr("desktop_2fa.cli.main.is_interactive", lambda: True)
    # urllib's IPv6-address error includes this host verbatim unless sanitized.
    uri = f"otpauth://[{SECRET}]/account?secret={SECRET}"
    if source == "issuer-prompt":
        monkeypatch.setattr(typer, "prompt", Mock(side_effect=["ignored-name", uri]))
        args = []
    else:
        args = [uri]
    result = CliRunner().invoke(
        app, ["--vault", str(path), "--password", PASSWORD, "add", *args]
    )
    assert result.exit_code == 6
    assert result.stderr == "Invalid otpauth URL: invalid provisioning data.\n"
    assert SECRET not in result.stdout + result.stderr
    assert uri not in result.stdout + result.stderr
    assert not path.exists()
