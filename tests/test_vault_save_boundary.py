"""Save-boundary regressions using synthetic data and selected temporary paths."""

from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from desktop_2fa.cli.main import app
from desktop_2fa.vault import TotpEntry, Vault, VaultData, VaultValidationError
from desktop_2fa.vault.vault import MAX_VAULT_SIZE

PASSWORD = "synthetic-save-boundary-password"
SECRET = "JBSWY3DPEHPK3PXP"


def _sized_vault(size: int, label: str) -> Vault:
    vault = Vault()
    vault.add_entry("synthetic", label, SECRET)
    # Size the padding using the actual serializer; the tests independently
    # check the resulting file size and retain the literal v1 overhead.
    payload = vault.data.model_dump_json().encode("utf-8")
    vault.entries[0].issuer = label + "x" * (size - 49 - len(payload))
    return vault


@pytest.mark.parametrize("label", ["ascii", 'żółw🔐"\\\n\t\x00'])
def test_save_exact_limit_and_one_byte_over(tmp_path: Path, label: str) -> None:
    path = tmp_path / "vault.bin"
    vault = _sized_vault(MAX_VAULT_SIZE, label)
    vault.save(path, PASSWORD)
    original = path.read_bytes()
    assert len(original) == MAX_VAULT_SIZE
    loaded = Vault.load(path, PASSWORD)
    assert loaded.data == vault.data

    assert loaded.entries[0].issuer is not None
    loaded.entries[0].issuer += "x"
    with pytest.raises(VaultValidationError, match="10485761 bytes; reduce"):
        loaded.save(path, PASSWORD)
    assert path.read_bytes() == original
    assert Vault.load(path, PASSWORD).data == vault.data
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("interactive", [False, True])
def test_cli_add_to_near_limit_preserves_existing_vault(
    tmp_path: Path, interactive: bool
) -> None:
    path = tmp_path / "vault.bin"
    vault = _sized_vault(MAX_VAULT_SIZE - 1, "synthetic")
    vault.save(path, PASSWORD)
    original = path.read_bytes()
    result = CliRunner().invoke(
        app,
        ["--vault", str(path), "--password", PASSWORD, "add", "new", "test", SECRET],
        env={"DESKTOP_2FA_FORCE_INTERACTIVE": "1" if interactive else "0"},
    )
    assert result.exit_code == 6, result.output
    assert "maximum supported size" in result.output
    assert "Invalid vault password" not in result.output
    assert "Entry added" not in result.output
    assert path.read_bytes() == original
    assert Vault.load(path, PASSWORD).data == vault.data
    assert list(tmp_path.iterdir()) == [path]


def test_cli_rename_to_exceed_limit_preserves_existing_vault(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"
    vault = _sized_vault(MAX_VAULT_SIZE - 1024, "synthetic")
    vault.add_entry("target", "test", SECRET)
    remaining = (
        MAX_VAULT_SIZE - 1 - 49 - len(vault.data.model_dump_json().encode("utf-8"))
    )
    assert vault.entries[0].issuer is not None
    vault.entries[0].issuer += "x" * remaining
    vault.save(path, PASSWORD)
    original = path.read_bytes()
    assert len(original) == MAX_VAULT_SIZE - 1

    result = CliRunner().invoke(
        app,
        [
            "--vault",
            str(path),
            "--password",
            PASSWORD,
            "rename",
            "target",
            "longer-name",
        ],
    )
    assert result.exit_code == 6, result.output
    assert "maximum supported size" in result.output
    assert "Invalid vault password" not in result.output
    assert "Renamed" not in result.output
    assert path.read_bytes() == original
    assert Vault.load(path, PASSWORD).data == vault.data
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize(
    "command",
    [
        ["remove", "synthetic"],
        ["rename", "synthetic", "new"],
        ["export", "{export}"],
        ["import", "{source}", "--force"],
        ["backup"],
        ["init-vault", "--force"],
        ["vault", "init", "--force"],
        ["vault", "change-password"],
        ["list"],
    ],
    ids=[
        "remove",
        "rename",
        "export",
        "import",
        "backup",
        "init",
        "vault-init",
        "password",
        "list-create",
    ],
)
def test_cli_save_validation_failure_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: list[str]
) -> None:
    path = tmp_path / "vault.bin"
    vault = Vault()
    vault.add_entry("synthetic", "test", SECRET)
    vault.save(path, PASSWORD)
    original = path.read_bytes()
    source = tmp_path / "source.bin"
    source.write_bytes(original)
    exported = tmp_path / "export.bin"
    exported.write_bytes(b"synthetic existing export")
    selected = tmp_path / "new.bin" if command == ["list"] else path

    def fail_save(self: Vault, path: str | Path, password: str) -> None:
        raise VaultValidationError(
            "Vault contains invalid data; correct entries before saving."
        )

    monkeypatch.setattr(Vault, "save", fail_save)
    monkeypatch.setattr(
        "desktop_2fa.cli.helpers.prompt_new_password",
        lambda ctx: "synthetic-new-password",
    )
    result = CliRunner().invoke(
        app,
        ["--vault", str(selected), "--password", PASSWORD, "--allow-weak-passwords"]
        + [arg.format(source=source, export=exported) for arg in command],
    )
    assert result.exit_code == 6, result.output
    assert "correct entries before saving" in result.output
    assert "Invalid vault password" not in result.output
    assert "Traceback" not in result.output
    for success in [
        "Removed entry:",
        "Renamed '",
        "Exported vault to:",
        "Vault imported from",
        "Backup created:",
        "Vault created at",
        "Vault password changed successfully.",
    ]:
        assert success not in result.output
    assert path.read_bytes() == original
    assert source.read_bytes() == original
    assert exported.read_bytes() == b"synthetic existing export"
    assert set(tmp_path.iterdir()) == {path, source, exported}


@pytest.mark.parametrize(
    ("field", "value"),
    [("period", 0), ("digits", 9), ("algorithm", "MD5"), ("secret", "!invalid!")],
)
def test_invalid_entry_mutation_preserves_previous_bytes(
    tmp_path: Path, field: str, value: Any
) -> None:
    path = tmp_path / "vault.bin"
    vault = Vault()
    vault.add_entry("synthetic", "test", SECRET)
    vault.save(path, PASSWORD)
    original = path.read_bytes()
    previous = Vault.load(path, PASSWORD).data
    setattr(vault.entries[0], field, value)
    with pytest.raises(
        VaultValidationError, match="correct entries before saving"
    ) as err:
        vault.save(path, PASSWORD)
    assert SECRET not in str(err.value)
    assert str(value) not in str(err.value)
    assert path.read_bytes() == original
    assert Vault.load(path, PASSWORD).data == previous
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("mutation", ["entry", "list", "version", "unserializable"])
def test_invalid_save_fails_before_kdf_or_filesystem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    vault = Vault()
    if mutation == "entry":
        vault.entries.append(TotpEntry.model_construct(secret=SECRET, period=0))
    elif mutation == "list":
        vault.data.entries = [None]  # type: ignore[list-item]
    elif mutation == "version":
        vault.data.version = "invalid"  # type: ignore[assignment]
    else:
        vault.data.entries = [object()]  # type: ignore[list-item]

    def unexpected(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("Invalid output must fail before KDF or filesystem operations")

    monkeypatch.setattr("desktop_2fa.vault.vault.derive_key", unexpected)
    monkeypatch.setattr("desktop_2fa.vault.vault.tempfile.mkstemp", unexpected)
    monkeypatch.setattr("desktop_2fa.vault.vault.os.replace", unexpected)
    path = tmp_path / "missing" / "vault.bin"
    with pytest.raises(VaultValidationError, match="correct entries before saving"):
        vault.save(path, PASSWORD)
    assert not path.parent.exists()


def test_oversized_save_fails_before_kdf_or_filesystem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault = _sized_vault(MAX_VAULT_SIZE + 1, "synthetic")

    def unexpected(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("Oversized output must fail before KDF or filesystem operations")

    monkeypatch.setattr("desktop_2fa.vault.vault.derive_key", unexpected)
    monkeypatch.setattr("desktop_2fa.vault.vault.tempfile.mkstemp", unexpected)
    monkeypatch.setattr("desktop_2fa.vault.vault.os.replace", unexpected)
    path = tmp_path / "missing" / "vault.bin"
    with pytest.raises(VaultValidationError, match="maximum supported size"):
        vault.save(path, PASSWORD)
    assert not path.parent.exists()


def test_save_preserves_supported_legacy_records(tmp_path: Path) -> None:
    # Existing models permit null/empty names, duplicate names and empty secrets.
    # Tightening new-entry policy is outside S04's save-boundary validation.
    vault = Vault(
        VaultData(
            entries=[
                TotpEntry(account_name=None, issuer=None, secret=""),
                TotpEntry(account_name="", issuer="", secret=SECRET.lower()),
                TotpEntry(account_name="duplicate", secret=SECRET, digits=7, period=45),
                TotpEntry(
                    account_name="duplicate",
                    secret=SECRET,
                    algorithm="SHA512",
                    digits=8,
                ),
            ]
        )
    )
    path = tmp_path / "legacy.bin"
    vault.save(path, PASSWORD)
    assert Vault.load(path, PASSWORD).data == vault.data


@pytest.mark.parametrize("operation", ["fsync", "replace"])
def test_io_failure_preserves_vault_and_unrelated_temporary_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    from desktop_2fa.vault.vault import VaultIOError

    path = tmp_path / "vault.bin"
    vault = Vault()
    vault.save(path, PASSWORD)
    original = path.read_bytes()
    sibling = tmp_path / ".vault.bin.unrelated.tmp"
    sibling.write_bytes(b"synthetic unrelated file")
    vault.add_entry("new", "synthetic", SECRET)

    def fail(*args: Any, **kwargs: Any) -> None:
        raise OSError("synthetic I/O failure")

    with monkeypatch.context() as scoped:
        scoped.setattr(f"desktop_2fa.vault.vault.os.{operation}", fail)
        with pytest.raises(VaultIOError, match="synthetic I/O failure"):
            vault.save(path, PASSWORD)
    assert path.read_bytes() == original
    assert Vault.load(path, PASSWORD).entries == []
    assert sibling.read_bytes() == b"synthetic unrelated file"
    assert set(tmp_path.iterdir()) == {path, sibling}
