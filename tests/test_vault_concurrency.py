"""Synchronized processes expose stale writes without timing-only sleeps."""

import multiprocessing as mp
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from desktop_2fa.cli.main import app
from desktop_2fa.vault import Vault, VaultConflict
from desktop_2fa.vault.locking import publication_lock
from desktop_2fa.vault.vault import InvalidPassword, VaultIOError

PASSWORD = "synthetic-concurrency-password"
SECRET = "JBSWY3DPEHPK3PXP"


def _add_worker(path, barrier, results, name):
    vault = Vault.load(path, PASSWORD)
    vault.add_entry(name, "synthetic", SECRET)
    barrier.wait(timeout=30)
    try:
        vault.save(path, PASSWORD)
    except VaultConflict:
        results.put("conflict")
    else:
        results.put("saved")


def test_two_stale_writers_cannot_both_succeed(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"
    Vault().save(path, PASSWORD)
    ctx = mp.get_context("spawn")
    barrier, results = ctx.Barrier(2), ctx.Queue()
    processes = [
        ctx.Process(target=_add_worker, args=(path, barrier, results, name))
        for name in ("first", "second")
    ]
    try:
        for process in processes:
            process.start()
        statuses = sorted(results.get(timeout=45) for _ in processes)
        for process in processes:
            process.join(timeout=30)
            assert process.exitcode == 0
        assert statuses == ["conflict", "saved"]
        assert len(Vault.load(path, PASSWORD).entries) == 1
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=10)


def _stale_worker(path, loaded, changed, results):
    vault = Vault.load(path, PASSWORD)
    vault.add_entry("stale", "synthetic", SECRET)
    loaded.set()
    assert changed.wait(timeout=30)
    try:
        vault.save(path, PASSWORD)
    except VaultConflict:
        results.put("conflict")
    else:
        results.put("saved")


def test_password_change_cannot_be_undone_by_stale_process(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"
    Vault().save(path, PASSWORD)
    ctx = mp.get_context("spawn")
    loaded, changed, results = ctx.Event(), ctx.Event(), ctx.Queue()
    process = ctx.Process(target=_stale_worker, args=(path, loaded, changed, results))
    process.start()
    try:
        assert loaded.wait(timeout=30)
        Vault.load(path, PASSWORD).save(path, "synthetic-new-password")
        changed.set()
        assert results.get(timeout=30) == "conflict"
        process.join(timeout=30)
        assert process.exitcode == 0
        assert Vault.load(path, "synthetic-new-password").entries == []
        with pytest.raises(InvalidPassword):
            Vault.load(path, PASSWORD)
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=10)


def _create_worker(path, barrier, results, name, command):
    # Freeze both CLI existence checks at the same absent snapshot.
    import desktop_2fa.cli.commands as commands

    def absent(path):
        barrier.wait(timeout=30)
        return False

    commands._vault_exists = absent
    if command == "add":
        arguments = ["add", name, "synthetic", SECRET]
    elif command == "import":
        arguments = ["import", str(path.with_name("source.bin"))]
    else:
        arguments = [command]
    result = CliRunner().invoke(
        app,
        [
            "--vault",
            str(path),
            "--password",
            PASSWORD,
            "--allow-weak-passwords",
            *arguments,
        ],
    )
    results.put(result.exit_code)


@pytest.mark.parametrize("command", ["add", "list", "init-vault", "import"])
def test_concurrent_cli_creation_preserves_winner(tmp_path: Path, command: str) -> None:
    path = tmp_path / "vault.bin"
    if command == "import":
        Vault().save(tmp_path / "source.bin", PASSWORD)
    ctx = mp.get_context("spawn")
    barrier, results = ctx.Barrier(2), ctx.Queue()
    processes = [
        ctx.Process(target=_create_worker, args=(path, barrier, results, name, command))
        for name in ("first", "second")
    ]
    try:
        for process in processes:
            process.start()
        assert sorted(results.get(timeout=45) for _ in processes) == [0, 6]
        for process in processes:
            process.join(timeout=30)
            assert process.exitcode == 0
        assert len(Vault.load(path, PASSWORD).entries) == (1 if command == "add" else 0)
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=10)


def _hold_lock(path, ready, release):
    with publication_lock(path):
        ready.set()
        assert release.wait(timeout=45)


@pytest.mark.parametrize("terminate", [False, True])
def test_lock_release_after_exit_or_termination(
    tmp_path: Path, terminate: bool
) -> None:
    path = tmp_path / "vault.bin"
    Vault().save(path, PASSWORD)
    ctx = mp.get_context("spawn")
    ready, release = ctx.Event(), ctx.Event()
    process = ctx.Process(target=_hold_lock, args=(path, ready, release))
    process.start()
    try:
        assert ready.wait(timeout=30)
        stale = Vault.load(path, PASSWORD)
        before = path.read_bytes()
        with pytest.raises(VaultConflict):
            stale.save(path, PASSWORD)
        assert path.read_bytes() == before
        if terminate:
            process.terminate()
        else:
            release.set()
        process.join(timeout=30)
        assert not process.is_alive()
        stale.save(path, PASSWORD)
        assert Vault.load(path, PASSWORD).entries == []
        assert (tmp_path / ".vault.bin.lock").read_bytes() == b""
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=10)


@pytest.mark.parametrize(
    "alias", ["relative", "case", "parent-symlink", "symlink", "hardlink"]
)
def test_aliases_do_not_bypass_revision_check(
    tmp_path: Path, alias: str, monkeypatch
) -> None:
    path = tmp_path / "vault.bin"
    Vault().save(path, PASSWORD)
    stale = Vault.load(path, PASSWORD)
    current = Vault.load(path, PASSWORD)
    current.add_entry("current", "synthetic", SECRET)
    current.save(path, PASSWORD)
    destination = tmp_path / "alias.bin"
    if alias == "relative":
        monkeypatch.chdir(tmp_path)
        destination = Path(".") / path.name
    elif alias == "case":
        destination = tmp_path / "VAULT.BIN"
        if not destination.exists():
            pytest.skip("Filesystem is case-sensitive")
    else:
        try:
            if alias == "hardlink":
                os.link(path, destination)
            elif alias == "symlink":
                destination.symlink_to(path)
            else:
                parent = tmp_path / "directory-alias"
                parent.symlink_to(tmp_path, target_is_directory=True)
                destination = parent / path.name
        except OSError as error:
            pytest.skip(f"Alias unsupported: {error}")
    before = path.read_bytes()
    with pytest.raises(VaultConflict):
        stale.save(destination, PASSWORD)
    assert path.read_bytes() == before
    assert destination.read_bytes() == before


def test_failed_publication_releases_lock_and_keeps_revision(
    tmp_path: Path, monkeypatch
) -> None:
    path = tmp_path / "vault.bin"
    vault = Vault()
    vault.save(path, PASSWORD)
    before = path.read_bytes()

    def fail(*args):
        raise OSError("synthetic replace failure")

    with monkeypatch.context() as scoped:
        scoped.setattr("desktop_2fa.vault.vault.os.replace", fail)
        with pytest.raises(VaultIOError):
            vault.save(path, PASSWORD)
    assert path.read_bytes() == before
    vault.save(path, PASSWORD)
    assert list(tmp_path.glob("*.tmp")) == []


def test_cli_reports_conflict_without_success(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "vault.bin"
    Vault().save(path, PASSWORD)
    original_load = Vault.load

    def intervening_load(path, password):
        stale = original_load(path, password)
        current = original_load(path, password)
        current.add_entry("current", "synthetic", SECRET)
        current.save(path, password)
        return stale

    monkeypatch.setattr(Vault, "load", intervening_load)
    result = CliRunner().invoke(
        app,
        [
            "--vault",
            str(path),
            "--password",
            PASSWORD,
            "add",
            "stale",
            "synthetic",
            SECRET,
        ],
    )
    assert result.exit_code == 6
    assert "Reload and retry" in result.output
    assert "Entry added" not in result.output
    assert [entry.account_name for entry in original_load(path, PASSWORD).entries] == [
        "current"
    ]


def test_deleted_revision_is_not_recreated(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"
    Vault().save(path, PASSWORD)
    stale = Vault.load(path, PASSWORD)
    path.unlink()
    with pytest.raises(VaultConflict):
        stale.save(path, PASSWORD)
    assert not path.exists()


def test_case_alias_save_updates_the_same_instances_revision(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"
    vault = Vault()
    vault.save(path, PASSWORD)
    alias = tmp_path / "VAULT.BIN"
    if not alias.exists():
        pytest.skip("Filesystem is case-sensitive")
    vault.save(alias, PASSWORD)
    vault.add_entry("next", "synthetic", SECRET)
    vault.save(path, PASSWORD)
    assert Vault.load(path, PASSWORD).get_entry("next").secret == SECRET


def test_occupied_lock_path_preserves_both_files(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"
    Vault().save(path, PASSWORD)
    vault = Vault.load(path, PASSWORD)
    before = path.read_bytes()
    lock = tmp_path / ".vault.bin.lock"
    lock.write_bytes(b"synthetic unrelated file")
    with pytest.raises(VaultIOError):
        vault.save(path, PASSWORD)
    assert path.read_bytes() == before
    assert lock.read_bytes() == b"synthetic unrelated file"
