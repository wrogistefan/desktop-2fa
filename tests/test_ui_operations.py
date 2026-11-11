"""UI persistence regressions use temporary vaults and synthetic credentials."""

from pathlib import Path

import pytest

from desktop_2fa.ui_textual.operations import FormError, perform
from desktop_2fa.vault import Vault
from desktop_2fa.vault.vault import (
    ExportRefused,
    InvalidPassword,
    VaultConflict,
    VaultIOError,
)

PASSWORD = "synthetic-ui-test-password"
SECRET = "JBSWY3DPEHPK3PXP"


@pytest.fixture
def unlocked(tmp_path: Path) -> tuple[Path, Vault]:
    path = tmp_path / "synthetic.bin"
    vault = Vault()
    vault.add_entry("first", "Example", SECRET, algorithm="SHA512", digits=8, period=45)
    vault.save(path, PASSWORD, overwrite=False)
    return path, vault


def test_complete_persistence_workflow(
    unlocked: tuple[Path, Vault], tmp_path: Path
) -> None:
    path, vault = unlocked
    values = {
        "password": PASSWORD,
        "name": "second",
        "issuer": "Example",
        "secret": SECRET,
    }
    vault = perform("add", path, vault, None, values).vault
    vault = perform(
        "rename", path, vault, 0, {"password": PASSWORD, "name": "renamed"}
    ).vault
    entry = vault.entries[0]
    assert (
        entry.account_name,
        entry.issuer,
        entry.algorithm,
        entry.digits,
        entry.period,
        entry.secret,
    ) == ("renamed", "renamed", "SHA512", 8, 45, SECRET)
    exported = tmp_path / "export.bin"
    perform("export", path, vault, None, {"password": PASSWORD, "file": str(exported)})
    perform("backup", path, vault, None, {"password": PASSWORD})
    perform("backup", path, vault, None, {"password": PASSWORD})
    for copy in (
        exported,
        path.with_suffix(".backup.bin"),
        path.with_suffix(".backup-1.bin"),
    ):
        assert Vault.load(copy, PASSWORD).data == vault.data
    vault = perform(
        "remove", path, vault, 1, {"password": PASSWORD, "confirm": "yes"}
    ).vault
    new_password = "synthetic-replacement-password"
    vault = perform(
        "change-password",
        path,
        vault,
        None,
        {
            "password": PASSWORD,
            "new-password": new_password,
            "confirm-password": new_password,
        },
        allow_weak=True,
    ).vault
    assert Vault.load(path, new_password).data == vault.data
    with pytest.raises(InvalidPassword):
        Vault.load(path, PASSWORD)
    restored = perform(
        "import",
        path,
        vault,
        None,
        {"password": PASSWORD, "file": str(exported), "overwrite": "yes"},
    ).vault
    # Imported sessions also carry the source revision: subsequent writes must work.
    restored = perform(
        "rename", path, restored, 1, {"password": PASSWORD, "name": "restored"}
    ).vault
    assert [entry.account_name for entry in restored.entries] == ["renamed", "restored"]


@pytest.mark.parametrize(
    "operation", ["add", "rename", "remove", "export", "backup", "change-password"]
)
def test_wrong_password_never_writes(
    unlocked: tuple[Path, Vault], operation: str
) -> None:
    path, vault = unlocked
    before = path.read_bytes()
    with pytest.raises(InvalidPassword):
        perform(operation, path, vault, 0, {"password": "synthetic-wrong"})
    assert path.read_bytes() == before
    assert vault.entries[0].account_name == "first"


@pytest.mark.parametrize(
    "operation", ["rename", "remove", "export", "backup", "change-password"]
)
def test_external_change_refuses_stale_selection(
    unlocked: tuple[Path, Vault], operation: str
) -> None:
    path, vault = unlocked
    other = Vault.load(path, PASSWORD)
    other.add_entry("external", "Example", SECRET)
    other.save(path, PASSWORD)
    before = path.read_bytes()
    with pytest.raises(VaultConflict):
        perform(
            operation,
            path,
            vault,
            0,
            {"password": PASSWORD, "name": "unsafe", "confirm": "yes"},
        )
    assert path.read_bytes() == before
    assert len(vault.entries) == 1


@pytest.mark.parametrize(
    "operation,extra",
    [
        ("add", {"name": "first", "issuer": "Example", "secret": SECRET}),
        ("add", {"uri": "otpauth://totp/Example:test?secret=invalid!"}),
        (
            "add",
            {"uri": "otpauth://totp/Example:test?secret=" + SECRET, "name": "conflict"},
        ),
        ("remove", {}),
        ("rename", {"name": " "}),
        (
            "change-password",
            {"new-password": "different", "confirm-password": "mismatch"},
        ),
    ],
)
def test_invalid_form_preserves_disk_and_session(
    unlocked: tuple[Path, Vault], operation: str, extra: dict[str, str]
) -> None:
    path, vault = unlocked
    before = path.read_bytes()
    data = vault.data.model_dump()
    with pytest.raises(ValueError):
        perform(operation, path, vault, 0, {"password": PASSWORD, **extra})
    assert path.read_bytes() == before
    assert vault.data.model_dump() == data


def test_io_failure_does_not_mutate_session(
    unlocked: tuple[Path, Vault], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, vault = unlocked
    before = path.read_bytes()

    def fail(*args: object, **kwargs: object) -> None:
        raise VaultIOError("synthetic write failure")

    monkeypatch.setattr(Vault, "save", fail)
    with pytest.raises(VaultIOError):
        perform("remove", path, vault, 0, {"password": PASSWORD, "confirm": "yes"})
    assert len(vault.entries) == 1
    assert path.read_bytes() == before


def test_import_and_create_refuse_implicit_replacement(
    unlocked: tuple[Path, Vault], tmp_path: Path
) -> None:
    path, vault = unlocked
    source = tmp_path / "source.bin"
    source.write_bytes(path.read_bytes())
    before = path.read_bytes()
    with pytest.raises(ExportRefused):
        perform(
            "create",
            path,
            vault,
            None,
            {"new-password": PASSWORD, "confirm-password": PASSWORD},
            allow_weak=True,
        )
    with pytest.raises(ExportRefused):
        perform(
            "import", path, vault, None, {"password": PASSWORD, "file": str(source)}
        )
    with pytest.raises(ExportRefused):
        perform(
            "import",
            path,
            vault,
            None,
            {"password": PASSWORD, "file": str(path), "overwrite": "yes"},
        )
    assert path.read_bytes() == before


def test_weak_password_requires_explicit_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from desktop_2fa.ui_textual import operations

    monkeypatch.setattr(operations.helpers, "load_config", lambda: {})
    values = {"new-password": "weak", "confirm-password": "weak"}
    path = tmp_path / "new.bin"
    with pytest.raises(FormError, match="weak"):
        perform("create", path, None, None, values)
    assert not path.exists()
    values["weak-password"] = "yes"
    perform("create", path, None, None, values)
    monkeypatch.setattr(
        operations.helpers,
        "load_config",
        lambda: {"security": {"reject_weak_passwords": True}},
    )
    with pytest.raises(FormError, match="too weak"):
        perform("create", tmp_path / "rejected.bin", None, None, values)


def test_uri_add_preserves_parameters(unlocked: tuple[Path, Vault]) -> None:
    path, vault = unlocked
    result = perform(
        "add",
        path,
        vault,
        None,
        {
            "password": PASSWORD,
            "uri": f"otpauth://totp/Example:uri-account?issuer=Example&secret={SECRET}&algorithm=SHA256&digits=7&period=60",
        },
    )
    entry = Vault.load(path, PASSWORD).entries[-1]
    assert (entry.account_name, entry.algorithm, entry.digits, entry.period) == (
        "uri-account",
        "SHA256",
        7,
        60,
    )
    assert result.vault.data == Vault.load(path, PASSWORD).data


def test_explicit_rows_repair_duplicate_names(tmp_path: Path) -> None:
    from desktop_2fa.vault.models import TotpEntry, VaultData

    path = tmp_path / "legacy-duplicate.bin"
    vault = Vault(
        VaultData(
            entries=[
                TotpEntry(account_name="duplicate", issuer="Example", secret=SECRET),
                TotpEntry(
                    account_name="duplicate", issuer="Example", secret="MY======"
                ),
            ]
        )
    )
    vault.save(path, PASSWORD)
    vault = perform(
        "rename", path, vault, 1, {"password": PASSWORD, "name": "repaired"}
    ).vault
    assert vault.entries[0].account_name == "duplicate"
    assert (
        vault.entries[1].account_name == "repaired"
        and vault.entries[1].secret == "MY======"
    )
    vault = perform(
        "remove", path, vault, 0, {"password": PASSWORD, "confirm": "yes"}
    ).vault
    assert len(vault.entries) == 1 and vault.entries[0].account_name == "repaired"


@pytest.mark.parametrize("tamper", [False, True])
def test_failed_import_preserves_destination(
    unlocked: tuple[Path, Vault], tmp_path: Path, tamper: bool
) -> None:
    path, vault = unlocked
    source = tmp_path / "source.bin"
    blob = bytearray(path.read_bytes())
    if tamper:
        blob[-1] ^= 1
    source.write_bytes(blob)
    before = path.read_bytes()
    with pytest.raises(InvalidPassword):
        perform(
            "import",
            path,
            vault,
            None,
            {
                "password": PASSWORD if tamper else "synthetic-wrong",
                "file": str(source),
                "overwrite": "yes",
            },
        )
    assert path.read_bytes() == before


@pytest.mark.parametrize("legacy_name", [None, ""])
def test_explicit_row_can_rename_an_unnamed_legacy_account(
    tmp_path: Path, legacy_name: str | None
) -> None:
    from desktop_2fa.vault.models import TotpEntry, VaultData

    path = tmp_path / "legacy-unnamed.bin"
    vault = Vault(
        VaultData(
            entries=[
                TotpEntry(account_name="shadow", issuer="Example", secret=SECRET),
                TotpEntry(
                    account_name=legacy_name,
                    issuer="shadow",
                    secret="MY======",
                    algorithm="SHA256",
                    period=45,
                    digits=8,
                ),
            ]
        )
    )
    vault.save(path, PASSWORD)
    before = path.read_bytes()
    with pytest.raises(FormError, match="occupied"):
        perform("rename", path, vault, 1, {"password": PASSWORD, "name": "shadow"})
    assert path.read_bytes() == before
    result = perform(
        "rename", path, vault, 1, {"password": PASSWORD, "name": "repaired"}
    )
    entry = result.vault.entries[1]
    assert (
        entry.account_name,
        entry.issuer,
        entry.secret,
        entry.algorithm,
        entry.period,
        entry.digits,
    ) == ("repaired", "repaired", "MY======", "SHA256", 45, 8)
    assert result.vault.entries[0].account_name == "shadow"
