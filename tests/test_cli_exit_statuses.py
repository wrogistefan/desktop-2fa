"""Automation must observe failed CLI operations without losing selected data."""

from pathlib import Path

import pytest
import typer
from click import Command
from typer.testing import CliRunner

from desktop_2fa.cli import helpers
from desktop_2fa.cli.main import app
from desktop_2fa.vault import Vault
from desktop_2fa.vault.vault import (
    CorruptedVault,
    InvalidPassword,
    PermissionDenied,
    UnsupportedFormat,
    VaultIOError,
    VaultNotFound,
    VaultValidationError,
)

PASSWORD = "synthetic-exit-status-password"
SECRET = "JBSWY3DPEHPK3PXP"
LOAD_COMMANDS = [
    ["add", "new", "test", SECRET],
    ["list"],
    ["code", "account"],
    ["remove", "account"],
    ["rename", "account", "new"],
    ["export", "{export}"],
    ["import", "{source}", "--force"],
    ["backup"],
    ["vault", "unlock"],
    ["vault", "change-password"],
    ["ui"],
]
SAVE_COMMANDS = [
    command + ["--force"] if command[0] == "export" else command
    for command in LOAD_COMMANDS
    if command[0] not in {"list", "code", "ui"} and command != ["vault", "unlock"]
] + [["init-vault", "--force"], ["vault", "init", "--force"]]
SUCCESS_MESSAGES = [
    "Entry added:",
    "Removed entry:",
    "Renamed '",
    "Exported vault to:",
    "Vault imported from",
    "Backup created:",
    "Vault created at",
    "Vault unlocked successfully.",
    "Vault password changed successfully.",
]


@pytest.fixture(scope="module")
def original_blob(tmp_path_factory: pytest.TempPathFactory) -> bytes:
    path = tmp_path_factory.mktemp("synthetic-status-source") / "vault.bin"
    vault = Vault()
    vault.add_entry("account", "test", SECRET)
    vault.save(path, PASSWORD)
    return path.read_bytes()


def _invoke(
    tmp_path: Path, original_blob: bytes, command: list[str], password: str = PASSWORD
):
    selected = tmp_path / "vault.bin"
    source = tmp_path / "source.bin"
    exported = tmp_path / "export.bin"
    selected.write_bytes(original_blob)
    source.write_bytes(original_blob)
    exported.write_bytes(b"synthetic-existing-output")
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    result = CliRunner().invoke(
        app,
        [
            "--vault",
            str(selected),
            "--password",
            password,
            "--allow-weak-passwords",
            *[arg.format(source=source, export=exported) for arg in command],
        ],
    )
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == before
    assert "Traceback" not in result.output
    assert SECRET not in result.output
    return result


@pytest.mark.parametrize("command", LOAD_COMMANDS, ids=lambda cmd: "-".join(cmd[:2]))
@pytest.mark.parametrize(
    "error,status",
    [
        (InvalidPassword, 2),
        (VaultNotFound, 4),
        (PermissionDenied, 1),
        (CorruptedVault, 1),
        (UnsupportedFormat, 1),
        (VaultIOError, 1),
        (RuntimeError, 1),
    ],
)
def test_typed_load_failures_across_commands(
    tmp_path: Path,
    original_blob: bytes,
    monkeypatch: pytest.MonkeyPatch,
    command: list[str],
    error: type[Exception],
    status: int,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise error("synthetic error detail that must not be disclosed")

    monkeypatch.setattr(Vault, "load", fail)
    result = _invoke(tmp_path, original_blob, command)
    assert result.exit_code == status, result.output
    assert "synthetic error detail" not in result.output
    for success in SUCCESS_MESSAGES:
        assert success not in result.output


@pytest.mark.parametrize("command", LOAD_COMMANDS, ids=lambda cmd: "-".join(cmd[:2]))
def test_actual_wrong_password_across_commands(
    tmp_path: Path, original_blob: bytes, command: list[str]
) -> None:
    result = _invoke(
        tmp_path, original_blob, command, password="synthetic-wrong-password"
    )
    assert result.exit_code == 2, result.output
    assert "Invalid vault password" in result.output
    for success in SUCCESS_MESSAGES:
        assert success not in result.output


@pytest.mark.parametrize("command", SAVE_COMMANDS, ids=lambda cmd: "-".join(cmd[:2]))
@pytest.mark.parametrize("status", [1, 6])
def test_save_failure_is_observable(
    tmp_path: Path,
    original_blob: bytes,
    monkeypatch: pytest.MonkeyPatch,
    command: list[str],
    status: int,
) -> None:
    monkeypatch.setattr(
        helpers, "prompt_new_password", lambda ctx: "synthetic-new-password"
    )

    def fail(*args: object, **kwargs: object) -> None:
        if status == 1:
            raise VaultIOError("synthetic write failure")
        raise VaultValidationError("synthetic validation failure")

    monkeypatch.setattr(Vault, "save", fail)
    result = _invoke(tmp_path, original_blob, command)
    assert result.exit_code == status, result.output
    for success in SUCCESS_MESSAGES:
        assert success not in result.output


@pytest.mark.parametrize(
    "command",
    [["code", "missing"], ["remove", "missing"], ["rename", "missing", "new"]],
)
def test_missing_entry_is_status_three(
    tmp_path: Path, original_blob: bytes, command: list[str]
) -> None:
    result = _invoke(tmp_path, original_blob, command)
    assert result.exit_code == 3, result.output
    assert "not found" in result.output
    for success in SUCCESS_MESSAGES:
        assert success not in result.output


@pytest.mark.parametrize(
    "command",
    [
        command
        for command in LOAD_COMMANDS
        if command[0] not in {"add", "list", "import"}
    ],
)
def test_missing_vault_is_status_four(tmp_path: Path, command: list[str]) -> None:
    result = CliRunner().invoke(
        app,
        [
            "--vault",
            str(tmp_path / "missing"),
            "--password",
            PASSWORD,
            *[arg.format(export=tmp_path / "export.bin") for arg in command],
        ],
    )
    assert result.exit_code == 4, result.output
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "command",
    [["add", "account", "test", SECRET], ["list"], ["init-vault"], ["vault", "init"]],
)
def test_new_vault_save_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: list[str]
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise VaultIOError("synthetic failure")

    monkeypatch.setattr(Vault, "save", fail)
    result = CliRunner().invoke(
        app, ["--vault", str(tmp_path / "new"), "--password", PASSWORD, *command]
    )
    assert result.exit_code == 1, result.output
    assert "Vault created at" not in result.output
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "command",
    [["remove", "account"], ["rename", "account", "new"], ["vault", "change-password"]],
)
def test_actual_failed_replace_preserves_old_bytes(
    tmp_path: Path,
    original_blob: bytes,
    monkeypatch: pytest.MonkeyPatch,
    command: list[str],
) -> None:
    monkeypatch.setattr(
        helpers, "prompt_new_password", lambda ctx: "synthetic-new-password"
    )

    def fail(*args: object, **kwargs: object) -> None:
        raise OSError("synthetic replace failure")

    monkeypatch.setattr("os.replace", fail)
    result = _invoke(tmp_path, original_blob, command)
    assert result.exit_code == 1, result.output
    assert (
        Vault.load(tmp_path / "vault.bin", PASSWORD).get_entry("account").secret
        == SECRET
    )


@pytest.mark.parametrize(
    "command", [["init-vault"], ["vault", "init"], ["import", "{source}"]]
)
def test_overwrite_refusal_is_validation_error(
    tmp_path: Path, original_blob: bytes, command: list[str]
) -> None:
    result = _invoke(tmp_path, original_blob, command)
    assert result.exit_code == 6, result.output


@pytest.mark.parametrize("detail", ["not found", "already exists", "password", SECRET])
def test_generic_value_error_never_drives_message_substring_classification(
    tmp_path: Path, original_blob: bytes, monkeypatch: pytest.MonkeyPatch, detail: str
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise ValueError(detail)

    monkeypatch.setattr(Vault, "get_entry", fail)
    result = _invoke(tmp_path, original_blob, ["code", "account"])
    assert result.exit_code == 6, result.output
    assert "Invalid input" in result.output
    assert detail not in result.output


@pytest.mark.parametrize(
    "error,status",
    [
        (InvalidPassword, 2),
        (VaultNotFound, 4),
        (PermissionDenied, 1),
        (CorruptedVault, 1),
        (UnsupportedFormat, 1),
        (VaultIOError, 1),
    ],
)
def test_load_cli_helper_does_not_swallow_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: type[Exception], status: int
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise error("synthetic private detail")

    monkeypatch.setattr(Vault, "load", fail)
    with pytest.raises(typer.Exit) as failure:
        helpers.load_vault_or_print_error(tmp_path / "selected", PASSWORD)
    assert failure.value.exit_code == status


@pytest.mark.parametrize("exists,status", [(False, 4), (None, 1)])
def test_ensure_cli_helper_does_not_return_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exists: bool | None, status: int
) -> None:
    monkeypatch.setattr("desktop_2fa.cli.commands._vault_exists", lambda path: exists)
    with pytest.raises(typer.Exit) as failure:
        helpers.ensure_existing_vault(tmp_path / "selected")
    assert failure.value.exit_code == status


@pytest.mark.parametrize(
    "interactive,answers",
    [
        (False, []),
        (True, [""]),
        (True, ["synthetic", ""]),
        (True, ["synthetic", "different"]),
    ],
)
def test_password_prompt_helper_does_not_return_none(
    monkeypatch: pytest.MonkeyPatch, interactive: bool, answers: list[str]
) -> None:
    values = iter(answers)
    monkeypatch.setattr("getpass.getpass", lambda prompt: next(values))
    ctx = typer.Context(Command("change-password"), obj={"interactive": interactive})
    with pytest.raises(typer.Exit) as failure:
        helpers.prompt_new_password(ctx)
    assert failure.value.exit_code == 6


def test_noninteractive_password_change_is_a_failure(
    tmp_path: Path, original_blob: bytes
) -> None:
    result = _invoke(tmp_path, original_blob, ["vault", "change-password"])
    assert result.exit_code == 6, result.output
    assert "requires interactive mode" in result.output
    assert "password changed successfully" not in result.output


def test_unlock_does_not_announce_success_before_config_failure(
    tmp_path: Path, original_blob: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail() -> None:
        raise OSError("synthetic configuration failure")

    monkeypatch.setattr(helpers, "load_config", fail)
    result = _invoke(tmp_path, original_blob, ["vault", "unlock"])
    assert result.exit_code == 1, result.output
    assert "Vault unlocked successfully" not in result.output


def test_successful_password_change_still_returns_zero(
    tmp_path: Path, original_blob: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    selected = tmp_path / "vault.bin"
    selected.write_bytes(original_blob)
    new_password = "synthetic-new-password"
    monkeypatch.setattr(helpers, "prompt_new_password", lambda ctx: new_password)
    result = CliRunner().invoke(
        app,
        [
            "--vault",
            str(selected),
            "--password",
            PASSWORD,
            "--allow-weak-passwords",
            "vault",
            "change-password",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Vault password changed successfully." in result.output
    assert Vault.load(selected, new_password).get_entry("account").secret == SECRET
    with pytest.raises(InvalidPassword):
        Vault.load(selected, PASSWORD)
