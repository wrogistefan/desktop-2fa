"""Directory metadata synchronization; filesystem/device guarantees still vary."""

import os
from pathlib import Path


def sync_parent(path: Path) -> None:
    """Sync a published directory entry on POSIX; no portable Windows equivalent.

    Errors propagate to the writer, which must report that publication already
    happened. This does not fsync newly created ancestor directories or request
    Apple's stronger F_FULLFSYNC device-cache operation.
    """
    if os.name != "posix":
        return
    fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
