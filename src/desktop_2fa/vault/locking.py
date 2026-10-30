"""Short, nonblocking OS locks for revision-check-and-replace publication."""

import os
import stat
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class LockBusy(OSError):
    """Another cooperating writer owns the publication lock."""


@contextmanager
def publication_lock(path: Path) -> Iterator[None]:
    """Keep the sidecar inode stable; closing releases the OS lock on exit.

    The empty sidecar is intentionally never deleted: unlinking it could let
    another writer lock a different inode. No password or vault data is stored.
    """
    path = path.resolve()
    lock_path = path.with_name(f".{path.name}.lock")
    if lock_path.is_symlink():
        raise OSError("Lock path must not be a symbolic link")
    fd = os.open(
        lock_path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600
    )
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size:
            raise OSError("Lock path must be a singly linked regular file")
        try:
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, PermissionError):
            raise LockBusy("Vault is being updated by another process") from None
        yield
    finally:
        os.close(fd)
