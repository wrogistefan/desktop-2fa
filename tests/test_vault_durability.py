"""Fault injection proves ordering/outcomes, not resilience to real power loss."""

import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from desktop_2fa.cli.errors import describe_error
from desktop_2fa.constants import ExitCode
from desktop_2fa.vault import Vault, VaultDurabilityError, durability
from desktop_2fa.vault import vault as writer

PASSWORD = "synthetic-durability-password"


@pytest.mark.parametrize("overwrite", [True, False])
def test_real_publication_order_and_roundtrip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, overwrite: bool
) -> None:
    path = tmp_path / "synthetic.bin"
    calls: list[str] = []
    original_fsync, original_replace, original_link = os.fsync, os.replace, os.link
    original_sync, original_unlink = writer.sync_parent, Path.unlink

    def fsync(fd: int) -> None:
        calls.append(
            "directory-fsync" if stat.S_ISDIR(os.fstat(fd).st_mode) else "file-fsync"
        )
        original_fsync(fd)

    def replace(source: Path, target: Path) -> None:
        calls.append("replace")
        original_replace(source, target)

    def link(source: Path, target: Path) -> None:
        calls.append("link")
        original_link(source, target)

    def unlink(target: Path, *args: object, **kwargs: object) -> None:
        calls.append("unlink")
        original_unlink(target, *args, **kwargs)

    def sync(target: Path) -> None:
        calls.append("sync-parent")
        original_sync(target)

    monkeypatch.setattr(os, "fsync", fsync)
    monkeypatch.setattr(os, "replace", replace)
    monkeypatch.setattr(os, "link", link)
    monkeypatch.setattr(Path, "unlink", unlink)
    monkeypatch.setattr(writer, "sync_parent", sync)
    vault = Vault()
    vault.add_entry("synthetic", "Example", "MY======")
    vault.save(path, PASSWORD, overwrite=overwrite)
    expected = (
        ["file-fsync", "replace"] if overwrite else ["file-fsync", "link", "unlink"]
    )
    expected += ["sync-parent"]
    if os.name == "posix":
        expected += ["directory-fsync"]
    assert calls == expected
    assert Vault.load(path, PASSWORD).data == vault.data
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("overwrite", [True, False])
@pytest.mark.parametrize(
    "error", [OSError("synthetic sync"), PermissionError("synthetic sync")]
)
def test_post_commit_failure_is_truthful_and_revision_supports_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, overwrite: bool, error: OSError
) -> None:
    path = tmp_path / "synthetic.bin"
    vault = Vault()
    if overwrite:
        vault.save(path, PASSWORD)
    vault.add_entry("new", "Example", "MY======")

    def fail(target: Path) -> None:
        raise error

    with monkeypatch.context() as scoped:
        scoped.setattr(writer, "sync_parent", fail)
        with pytest.raises(VaultDurabilityError, match="Vault was written") as caught:
            vault.save(path, PASSWORD, overwrite=overwrite)
    assert describe_error(caught.value) == (
        ExitCode.GENERAL_ERROR,
        "vault_durability_uncertain",
        str(caught.value),
    )
    assert Vault.load(path, PASSWORD).data == vault.data
    assert not list(tmp_path.glob("*.tmp"))
    # The same instance remembers its committed revision, not the stale baseline.
    vault.add_entry("retry", "Example", "MZXQ====")
    vault.save(path, PASSWORD)
    assert len(Vault.load(path, PASSWORD).entries) == 2


@pytest.mark.parametrize("failure", [False, True])
def test_posix_directory_descriptor_is_closed_on_success_and_failure(
    monkeypatch: pytest.MonkeyPatch, failure: bool
) -> None:
    calls: list[object] = []

    def open_directory(path: Path, flags: int) -> int:
        calls.append((path, flags))
        return 123

    def fsync(fd: int) -> None:
        calls.append(("fsync", fd))
        if failure:
            raise OSError("synthetic unsupported directory sync")

    fake_os = SimpleNamespace(
        name="posix",
        O_RDONLY=0,
        O_DIRECTORY=65536,
        open=open_directory,
        fsync=fsync,
        close=lambda fd: calls.append(("close", fd)),
    )
    monkeypatch.setattr(durability, "os", fake_os)
    path = Path("synthetic") / "vault.bin"
    if failure:
        with pytest.raises(OSError, match="synthetic unsupported"):
            durability.sync_parent(path)
    else:
        durability.sync_parent(path)
    assert calls == [(path.parent, 65536), ("fsync", 123), ("close", 123)]


def test_windows_skips_posix_directory_operations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(durability, "os", SimpleNamespace(name="nt"))
    durability.sync_parent(Path("synthetic-not-opened"))


def test_create_only_cleanup_failure_reports_committed_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "synthetic.bin"
    original_unlink = Path.unlink
    attempts = []

    def fail_once(target: Path) -> None:
        attempts.append(target)
        if len(attempts) == 1:
            raise OSError("synthetic unlink failure")
        original_unlink(target)

    vault = Vault()
    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "unlink", fail_once)
        with pytest.raises(VaultDurabilityError, match="Vault was written"):
            vault.save(path, PASSWORD, overwrite=False)
    assert Vault.load(path, PASSWORD).data == vault.data
    assert len(attempts) == 2
    assert path not in attempts
    assert not list(tmp_path.glob("*.tmp"))
