"""Rename safety and explicit legacy-duplicate repair with synthetic entries."""

import base64
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from desktop_2fa.cli import helpers
from desktop_2fa.cli.main import app
from desktop_2fa.vault import (
    AmbiguousEntry,
    EntryRenameError,
    TotpEntry,
    Vault,
    VaultData,
)

PASSWORD = "synthetic-rename-password"


def _entry(name: str | None, issuer: str | None, number: int = 0) -> TotpEntry:
    return TotpEntry(
        account_name=name,
        issuer=issuer,
        secret=base64.b32encode(f"synthetic-secret-{number}".encode()).decode(),
        algorithm=["SHA1", "SHA256", "SHA512"][number % 3],
        digits=[6, 7, 8][number % 3],
        period=[30, 45, 60][number % 3],
    )


def _duplicates() -> Vault:
    return Vault(
        VaultData(
            entries=[
                _entry("GitHub", issuer, i)
                for i, issuer in enumerate(["personal", "work", "test"])
            ]
        )
    )


@pytest.mark.parametrize("index", [None, 1])
def test_occupied_destination_rejected_before_mutation(index: int | None) -> None:
    vault = Vault(
        VaultData(entries=[_entry("old", "issuer"), _entry("taken", "other")])
    )
    before = vault.data.model_dump()
    with pytest.raises(EntryRenameError, match="already exists"):
        vault.rename_entry("old", "taken", index=index)
    assert vault.data.model_dump() == before


@pytest.mark.parametrize("index", [None, 1])
def test_unique_self_rename_preserves_issuer_update_semantics(
    index: int | None,
) -> None:
    vault = Vault(VaultData(entries=[_entry("account", "different-issuer")]))
    before = vault.entries[0].model_dump()
    vault.rename_entry("account", "account", index=index)
    assert vault.entries[0].model_dump() == {**before, "issuer": "account"}


def test_duplicate_self_rename_is_still_an_occupied_destination() -> None:
    vault = _duplicates()
    before = vault.data.model_dump()
    with pytest.raises(EntryRenameError, match="already exists"):
        vault.rename_entry("GitHub", "GitHub", index=2)
    assert vault.data.model_dump() == before


def test_identical_legacy_records_change_only_at_selected_index() -> None:
    first = _entry("duplicate", "same-issuer")
    second = first.model_copy(deep=True)
    vault = Vault(VaultData(entries=[first, second]))
    before = first.model_dump()
    vault.rename_entry("duplicate", "repaired", index=2)
    assert first.model_dump() == before
    assert second.model_dump() == {
        **before,
        "account_name": "repaired",
        "issuer": "repaired",
    }


@pytest.mark.parametrize("reverse", [False, True])
def test_exact_name_precedes_issuer_and_destination_issuer_is_allowed(
    reverse: bool,
) -> None:
    target = _entry("target", "source", 0)
    shadow = _entry("other", "target", 1)
    issuer_collision = _entry("third", "new", 2)
    entries = [target, shadow, issuer_collision]
    vault = Vault(VaultData(entries=entries[::-1] if reverse else entries))
    vault.rename_entry("target", "new")
    assert vault.get_entry("new") is target
    assert target.issuer == "new"
    assert shadow.account_name == "other"
    assert shadow.issuer == "target"
    assert issuer_collision.account_name == "third"
    assert issuer_collision.issuer == "new"


def test_rename_by_unique_issuer_and_case_sensitive_destination() -> None:
    vault = Vault(VaultData(entries=[_entry(None, "source"), _entry("NEW", "other")]))
    vault.rename_entry("source", "new")
    assert vault.entries[0].account_name == "new"
    assert vault.entries[0].issuer == "new"
    assert vault.entries[1].account_name == "NEW"


@pytest.mark.parametrize("index", [0, -1, 4, True, "1", 1.5])
def test_invalid_index_never_mutates_data(index: Any) -> None:
    vault = _duplicates()
    before = vault.data.model_dump()
    with pytest.raises(EntryRenameError, match="Invalid entry index"):
        vault.rename_entry("GitHub", "new", index=index)
    assert vault.data.model_dump() == before


@pytest.mark.parametrize("old", ["missing", "source"])
def test_index_cannot_bypass_old_name_resolution_tier(old: str) -> None:
    vault = Vault(
        VaultData(entries=[_entry("first", "source"), _entry("source", "other")])
    )
    before = vault.data.model_dump()
    with pytest.raises(EntryRenameError, match="does not match"):
        vault.rename_entry(old, "new", index=1)
    assert vault.data.model_dump() == before


@pytest.mark.parametrize("name", [None, ""])
def test_explicit_index_repairs_duplicate_legacy_issuers(name: str | None) -> None:
    vault = Vault(
        VaultData(entries=[_entry(name, "source", 0), _entry(name, "source", 1)])
    )
    before = vault.entries[0].model_dump()
    with pytest.raises(AmbiguousEntry):
        vault.rename_entry("source", "new")
    vault.rename_entry("source", "new", index=2)
    assert vault.entries[0].model_dump() == before
    assert vault.entries[1].account_name == "new"


def test_documented_cli_duplicate_repair_preserves_all_totp_data(
    tmp_path: Path,
) -> None:
    path = tmp_path / "legacy-vault.bin"
    vault = _duplicates()
    vault.save(path, PASSWORD)
    before = vault.data.model_dump()
    runner = CliRunner()
    prefix = ["--vault", str(path), "--password", PASSWORD]
    listed = runner.invoke(app, prefix + ["list", "--indices"])
    assert listed.exit_code == 0, listed.output
    for i, entry in enumerate(vault.entries, 1):
        assert f"[{i}] 'GitHub' ({entry.issuer!r})" in listed.output
        assert entry.secret not in listed.output

    for index, new in enumerate(["GitHub-personal", "GitHub-work", "GitHub-test"], 1):
        result = runner.invoke(
            app, prefix + ["rename", "GitHub", new, "--index", str(index)]
        )
        assert result.exit_code == 0, result.output
        expected = before["entries"][index - 1]
        expected["account_name"] = new
        expected["issuer"] = new
        loaded = Vault.load(path, PASSWORD)
        assert loaded.data.model_dump() == before
        for original, actual in zip(vault.entries, loaded.entries, strict=True):
            assert base64.b32decode(actual.secret) == base64.b32decode(original.secret)


@pytest.mark.parametrize("via_helper", [False, True], ids=["cli", "helper"])
@pytest.mark.parametrize(
    ("old", "new", "index", "error"),
    [
        ("GitHub", "unique", None, AmbiguousEntry),
        ("GitHub", "unique", 0, EntryRenameError),
        ("GitHub", "unique", 4, EntryRenameError),
        ("missing", "unique", 2, EntryRenameError),
        ("GitHub", "GitHub", 2, EntryRenameError),
    ],
)
def test_cli_and_helper_rejections_preserve_file(
    tmp_path: Path,
    via_helper: bool,
    old: str,
    new: str,
    index: int | None,
    error: type[ValueError],
) -> None:
    path = tmp_path / "legacy.bin"
    vault = _duplicates()
    vault.save(path, PASSWORD)
    original = path.read_bytes()
    if via_helper:
        with pytest.raises(error):
            helpers.rename_entry(path, old, new, PASSWORD, index=index)
    else:
        args = ["--vault", str(path), "--password", PASSWORD, "rename", old, new]
        if index is not None:
            args += ["--index", str(index)]
        result = CliRunner().invoke(app, args)
        assert result.exit_code == 6, result.output
        assert "Renamed" not in result.output
        assert "Invalid vault password" not in result.output
    assert path.read_bytes() == original
    assert Vault.load(path, PASSWORD).data == vault.data


def test_helper_repairs_only_selected_duplicate(tmp_path: Path) -> None:
    path = tmp_path / "legacy.bin"
    vault = _duplicates()
    before = vault.data.model_dump()
    vault.save(path, PASSWORD)
    helpers.rename_entry(path, "GitHub", "GitHub-work", PASSWORD, index=2)
    before["entries"][1].update(account_name="GitHub-work", issuer="GitHub-work")
    assert Vault.load(path, PASSWORD).data.model_dump() == before


@pytest.mark.parametrize("via_helper", [False, True], ids=["cli", "helper"])
def test_occupied_other_account_preserves_file(
    tmp_path: Path, via_helper: bool
) -> None:
    path = tmp_path / "vault.bin"
    vault = Vault(
        VaultData(entries=[_entry("old", "first"), _entry("taken", "second")])
    )
    vault.save(path, PASSWORD)
    original = path.read_bytes()
    if via_helper:
        with pytest.raises(EntryRenameError, match="already exists"):
            helpers.rename_entry(path, "old", "taken", PASSWORD)
    else:
        result = CliRunner().invoke(
            app,
            ["--vault", str(path), "--password", PASSWORD, "rename", "old", "taken"],
        )
        assert result.exit_code == 6, result.output
        assert "already exists" in result.output
        assert "Renamed" not in result.output
    assert path.read_bytes() == original
    assert Vault.load(path, PASSWORD).data == vault.data


@pytest.mark.parametrize("index", ["not-a-number", "1.5"])
def test_cli_malformed_index_is_usage_error_without_file_changes(
    tmp_path: Path, index: str
) -> None:
    path = tmp_path / "vault.bin"
    vault = _duplicates()
    vault.save(path, PASSWORD)
    original = path.read_bytes()
    result = CliRunner().invoke(
        app,
        [
            "--vault",
            str(path),
            "--password",
            PASSWORD,
            "rename",
            "GitHub",
            "new",
            "--index",
            index,
        ],
    )
    assert result.exit_code == 2, result.output
    assert "Renamed" not in result.output
    assert path.read_bytes() == original


def test_indices_are_opt_in_and_escape_multiline_labels(capsys: Any) -> None:
    entries = [_entry("line\nbreak", "issuer\tlabel")]
    helpers.print_entries_table(entries, show_indices=True)
    assert capsys.readouterr().out == "[1] 'line\\nbreak' ('issuer\\tlabel')\n"
    helpers.print_entries_table([_entry("account", "issuer")])
    assert capsys.readouterr().out == "- account (issuer)\n"
