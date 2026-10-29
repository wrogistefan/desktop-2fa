"""Complete stdout is a single JSON object or a raw code, even on early failures."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from desktop_2fa.cli.main import app
from desktop_2fa.vault import Vault
from desktop_2fa.vault.models import TotpEntry, VaultData

PASSWORD = "synthetic-output-password"
SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"


@pytest.fixture
def selected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr("desktop_2fa.cli.main.is_interactive", lambda: False)
    monkeypatch.setattr("desktop_2fa.cli.commands.time.time", lambda: 59)
    path = tmp_path / "synthetic.bin"
    vault = Vault(
        VaultData(
            entries=[
                TotpEntry(
                    account_name="account", issuer="test", secret=SECRET, digits=8
                ),
                TotpEntry(account_name="duplicate", issuer="one", secret=SECRET),
                TotpEntry(account_name="duplicate", issuer="two", secret=SECRET),
            ]
        )
    )
    vault.save(path, PASSWORD)
    return path


def invoke(path, args, password=True):
    flags = ["--password", PASSWORD] if password else []
    return CliRunner().invoke(app, ["--vault", str(path), *flags, *args])


def test_json_success_with_legacy_duplicates(selected):
    result = invoke(selected, ["code", "account", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {
        "account": "account",
        "issuer": "test",
        "code": "94287082",
        "valid_for": 1,
    }
    assert "multiple entries" in result.stderr
    assert "duplicate" not in result.stderr
    assert PASSWORD not in result.stderr and SECRET not in result.stderr


@pytest.mark.parametrize(
    "extra,status,error",
    [
        (["--raw"], 6, "invalid_options"),
        (["--quiet"], 6, "invalid_options"),
        (["--copy"], 6, "invalid_options"),
        (["--copy-only"], 6, "invalid_options"),
        (["--copy", "--copy-only"], 6, "invalid_options"),
        (["--unknown"], 2, "usage_error"),
    ],
)
def test_json_option_errors(selected, extra, status, error):
    result = invoke(selected, ["code", "account", "--json", *extra])
    assert result.exit_code == status
    assert json.loads(result.stdout)["error"] == error
    assert result.stderr == ""


@pytest.mark.parametrize(
    "flags,status",
    [
        ([], 6),
        (["--password", ""], 6),
        (["--password-file", "{missing}"], 1),
        (["--password-file", "{empty}"], 6),
        (["--password", PASSWORD, "--password-file", "{missing}"], 6),
    ],
)
@pytest.mark.parametrize("mode", ["--json", "--raw", "--quiet"])
def test_password_failures(selected, tmp_path, flags, status, mode):
    empty = tmp_path / "empty.txt"
    empty.write_text("")
    flags = [x.format(missing=tmp_path / "missing.txt", empty=empty) for x in flags]
    result = invoke(selected, [*flags, "code", "account", mode], password=False)
    assert result.exit_code == status
    if mode == "--json":
        assert json.loads(result.stdout)["error"] == "password_error"
        assert result.stderr == ""
    else:
        assert result.stdout == ""
        assert bool(result.stderr) == (mode != "--quiet")


@pytest.mark.parametrize(
    "case,status,error",
    [
        ("missing", 4, "vault_missing"),
        ("corrupt", 1, "unsupported_format"),
        ("wrong_password", 2, "invalid_password"),
        ("no_entry", 3, "entry_not_found"),
        ("ambiguous", 6, "entry_ambiguous"),
    ],
)
@pytest.mark.parametrize("mode", ["--json", "--raw", "--quiet"])
def test_load_and_lookup_failures(selected, case, status, error, mode):
    name = "account"
    password = PASSWORD
    if case == "missing":
        selected.unlink()
    elif case == "corrupt":
        selected.write_bytes(b"synthetic-corrupt-vault")
    elif case == "wrong_password":
        password = "synthetic-wrong-password"
    elif case == "no_entry":
        name = "absent"
    elif case == "ambiguous":
        name = "duplicate"
    result = invoke(
        selected, ["--password", password, "code", name, mode], password=False
    )
    assert result.exit_code == status
    if mode == "--json":
        data = json.loads(result.stdout)
        assert set(data) == {"error", "message"}
        assert data["error"] == error
    else:
        assert result.stdout == ""
        assert bool(result.stderr) == (mode != "--quiet")


@pytest.mark.parametrize("mode,stdout", [("--raw", "94287082\n"), ("--quiet", "")])
def test_raw_and_quiet_success(selected, mode, stdout):
    result = invoke(selected, ["code", "account", mode])
    assert result.exit_code == 0
    assert result.stdout == stdout
    assert bool(result.stderr) == (mode == "--raw")


@pytest.mark.parametrize(
    "args",
    [
        ["code", "--json"],
        ["code", "account", "--json", "--password-file"],
    ],
)
def test_json_parser_errors(selected, args):
    result = invoke(selected, args)
    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"] == "usage_error"
    assert result.stderr == ""


def test_unexpected_failure_and_interactive_abort(selected, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError(SECRET)

    monkeypatch.setattr(Vault, "load", broken)
    result = invoke(selected, ["code", "account", "--json"])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"] == "operation_failed"
    assert SECRET not in result.output
    monkeypatch.setattr("desktop_2fa.cli.main.is_interactive", lambda: True)

    def aborted(*args):
        raise EOFError

    monkeypatch.setattr("desktop_2fa.cli.helpers.getpass.getpass", aborted)
    result = invoke(selected, ["code", "account", "--json"], password=False)
    assert result.exit_code == 6
    assert json.loads(result.stdout)["error"] == "input_aborted"
    assert "Enter vault password" in result.stderr


@pytest.mark.parametrize(
    "timestamp,code,remaining", [(59, "94287082", 1), (60, "37359152", 30)]
)
def test_json_period_boundary(selected, monkeypatch, timestamp, code, remaining):
    monkeypatch.setattr("desktop_2fa.cli.commands.time.time", lambda: timestamp)
    result = invoke(selected, ["code", "account", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["code"] == code
    assert data["valid_for"] == remaining


def test_corrupted_payload_json(selected, monkeypatch):
    from desktop_2fa.vault.vault import CorruptedVault

    def corrupt(*args, **kwargs):
        raise CorruptedVault(SECRET)

    monkeypatch.setattr(Vault, "load", corrupt)
    result = invoke(selected, ["code", "account", "--json"])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"] == "corrupted_vault"
    assert result.stderr == ""


@pytest.mark.parametrize("mode", ["--raw", "--quiet"])
def test_parser_streams(selected, mode):
    result = invoke(selected, ["code", "account", mode, "--unknown"])
    assert result.exit_code == 2
    assert result.stdout == ""
    assert bool(result.stderr) == (mode == "--raw")


def test_mode_does_not_leak_between_invocations(selected):
    first = invoke(selected, ["code", "account", "--quiet"])
    second = invoke(selected, ["code", "account"])
    assert first.output == ""
    assert second.stdout == "94287082 (valid 1s)\n"
    assert "multiple entries" in second.stderr


def test_quiet_never_prompts_for_password(selected, monkeypatch):
    monkeypatch.setattr("desktop_2fa.cli.main.is_interactive", lambda: True)

    def unexpected_prompt(*args):
        raise AssertionError("quiet must not prompt")

    monkeypatch.setattr("desktop_2fa.cli.helpers.getpass.getpass", unexpected_prompt)
    result = invoke(selected, ["code", "account", "--quiet"], password=False)
    assert result.exit_code == 6
    assert result.stdout == result.stderr == ""


@pytest.mark.parametrize("mode", ["--json", "--raw"])
def test_interactive_password_keeps_stdout_clean(selected, monkeypatch, mode):
    monkeypatch.setattr("desktop_2fa.cli.main.is_interactive", lambda: True)
    monkeypatch.setattr("desktop_2fa.cli.helpers.getpass.getpass", lambda _: PASSWORD)
    result = invoke(selected, ["code", "account", mode], password=False)
    assert result.exit_code == 0
    if mode == "--json":
        assert json.loads(result.stdout)["code"] == "94287082"
    else:
        assert result.stdout == "94287082\n"
    assert "Enter vault password" in result.stderr
    assert PASSWORD not in result.output


@pytest.mark.parametrize("copy_flag,status", [("--copy", 0), ("--copy-only", 5)])
def test_quiet_clipboard_failure_streams(selected, monkeypatch, copy_flag, status):
    from desktop_2fa.cli.clipboard import ClipboardError

    def unavailable(*args):
        raise ClipboardError(SECRET)

    monkeypatch.setattr("desktop_2fa.cli.clipboard.copy_to_clipboard", unavailable)
    result = invoke(selected, ["code", "account", "--quiet", copy_flag])
    assert result.exit_code == status
    assert result.stdout == result.stderr == ""
