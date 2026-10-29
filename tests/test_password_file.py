"""Synthetic password files preserve exact credentials without fallback or writes."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import typer
from typer.testing import CliRunner

from desktop_2fa.cli import helpers
from desktop_2fa.cli.main import app
from desktop_2fa.vault import Vault

SECRET = "JBSWY3DPEHPK3PXP"
PASSWORDS = [
    "  synthetic passphrase  ",
    "\t synthetic\tpassword \t",
    "  zażółć 密碼 🔐  ",
    "synthetic-café",
    "synthetic-cafe\u0301",
    " \t ",
]


@pytest.mark.parametrize("password", PASSWORDS)
@pytest.mark.parametrize("ending", [b"", b"\n", b"\r\n"])
def test_exact_file_decoding(tmp_path, password, ending):
    path = tmp_path / "synthetic-password.txt"
    path.write_bytes(password.encode("utf-8") + ending)
    assert helpers._read_password_file(str(path)) == password
    ctx = SimpleNamespace(obj={"password_file": str(path), "interactive": False})
    assert helpers.get_password_for_vault(ctx) == password


@pytest.mark.parametrize("password", PASSWORDS)
def test_same_password_via_api_prompt_flag_and_file(tmp_path, monkeypatch, password):
    selected = tmp_path / "synthetic-vault.bin"
    password_file = tmp_path / "synthetic-password.txt"
    password_file.write_bytes(password.encode("utf-8") + b"\r\n")
    vault = Vault()
    vault.add_entry("account", "test", SECRET)
    vault.save(selected, password)
    before = selected.read_bytes()
    assert Vault.load(selected, password).entries == vault.entries
    monkeypatch.setattr("desktop_2fa.cli.main.is_interactive", lambda: True)
    prompt = Mock(return_value=password)
    monkeypatch.setattr(helpers.getpass, "getpass", prompt)
    for flags in [
        [],
        ["--password", password],
        ["--password-file", str(password_file)],
    ]:
        result = CliRunner().invoke(app, ["--vault", str(selected), *flags, "list"])
        assert result.exit_code == 0, result.output
        assert "account" in result.stdout
        assert selected.read_bytes() == before
        assert password not in result.output
    prompt.assert_called_once_with("")


@pytest.mark.parametrize(
    "blob",
    [
        b"",
        b"\n",
        b"\r\n",
        b"synthetic\r",
        b"synthetic\n\n",
        b"synthetic\r\n\r\n",
        b"one\ntwo",
        b"one\rtwo",
        b"one\r\ntwo",
        b"\xffsynthetic",
        b"\xc3",
        b"\xef\xbb\xbfsynthetic",
        b"\xff\xfes\x00",
    ],
)
def test_malformed_file_fails_without_contents(tmp_path, capsys, blob):
    path = tmp_path / "synthetic-password.txt"
    path.write_bytes(blob)
    with pytest.raises(typer.Exit) as error:
        helpers._read_password_file(str(path))
    assert error.value.exit_code == 6
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err
    assert "synthetic" not in captured.err
    assert str(path) not in captured.err


@pytest.mark.parametrize(
    "blob", [b"", b"\xffsynthetic", b"synthetic\n\n", b"\xef\xbb\xbfsynthetic"]
)
@pytest.mark.parametrize("mode", ["--json", "--raw", "--quiet"])
def test_invalid_file_uses_cli_stream_contract(tmp_path, monkeypatch, blob, mode):
    selected = tmp_path / "synthetic-vault.bin"
    selected.write_bytes(b"synthetic-placeholder")
    password_file = tmp_path / "synthetic-password.txt"
    password_file.write_bytes(blob)
    load = Mock(side_effect=AssertionError("must not load"))
    save = Mock(side_effect=AssertionError("must not write"))
    monkeypatch.setattr(Vault, "load", load)
    monkeypatch.setattr(Vault, "save", save)
    result = CliRunner().invoke(
        app,
        [
            "--vault",
            str(selected),
            "--password-file",
            str(password_file),
            "code",
            "account",
            mode,
        ],
    )
    assert result.exit_code == 6
    if mode == "--json":
        assert json.loads(result.stdout)["error"] == "password_error"
        assert result.stderr == ""
    else:
        assert result.stdout == ""
        assert bool(result.stderr) == (mode == "--raw")
    assert "synthetic" not in result.output
    load.assert_not_called()
    save.assert_not_called()
    assert selected.read_bytes() == b"synthetic-placeholder"


@pytest.mark.parametrize("error", [FileNotFoundError, PermissionError, OSError])
def test_unreadable_password_file(tmp_path, monkeypatch, capsys, error):
    def unreadable(*args, **kwargs):
        raise error("synthetic-private-file-content")

    monkeypatch.setattr("builtins.open", unreadable)
    with pytest.raises(typer.Exit) as failure:
        helpers._read_password_file(str(tmp_path / "synthetic.txt"))
    assert failure.value.exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err
    assert "synthetic" not in captured.err


@pytest.mark.parametrize(
    "command",
    [
        ["vault", "unlock"],
        ["list"],
        ["add", "new", "test", SECRET],
        ["vault", "change-password"],
    ],
)
@pytest.mark.parametrize(
    "stored,supplied",
    [
        ("synthetic-old-password", "  synthetic-old-password  "),
        ("  synthetic-password  ", "synthetic-password"),
    ],
)
def test_failed_unlock_never_retries_or_writes(
    tmp_path, monkeypatch, command, stored, supplied
):
    selected = tmp_path / "synthetic-vault.bin"
    password_file = tmp_path / "synthetic-password.txt"
    password_file.write_bytes(supplied.encode("utf-8") + b"\n")
    vault = Vault()
    vault.add_entry("account", "test", SECRET)
    vault.save(selected, stored)
    before = selected.read_bytes()
    load = Mock(wraps=Vault.load)
    save = Mock(side_effect=AssertionError("must not save"))
    prompt = Mock(side_effect=AssertionError("must not prompt"))
    monkeypatch.setattr(Vault, "load", load)
    monkeypatch.setattr(Vault, "save", save)
    monkeypatch.setattr(helpers.getpass, "getpass", prompt)
    result = CliRunner().invoke(
        app, ["--vault", str(selected), "--password-file", str(password_file), *command]
    )
    assert result.exit_code == 2
    load.assert_called_once_with(selected, supplied)
    save.assert_not_called()
    prompt.assert_not_called()
    assert selected.read_bytes() == before
    assert stored not in result.output and supplied not in result.output


@pytest.mark.parametrize("source", ["flag", "file"])
def test_supplied_password_does_not_expand_strength_check_scope(
    tmp_path, monkeypatch, source
):
    password_file = tmp_path / "synthetic-password.txt"
    password_file.write_bytes(b" \t ")
    obj = {"interactive": True}
    obj.update(
        {"password": " \t "}
        if source == "flag"
        else {"password_file": str(password_file)}
    )
    enforce = Mock(
        side_effect=AssertionError("supplied passwords bypass creation strength checks")
    )
    monkeypatch.setattr(helpers, "_enforce_password_strength", enforce)
    assert (
        helpers.get_password_for_vault(SimpleNamespace(obj=obj), new_vault=True)
        == " \t "
    )
    enforce.assert_not_called()
