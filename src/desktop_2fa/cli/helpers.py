from __future__ import annotations

from pathlib import Path
from desktop_2fa.storage import Storage

VAULT_PATH = "vault.json"


def load_vault() -> Storage:
    """Load plaintext vault (Storage)."""
    if not Path(VAULT_PATH).exists():
        # create empty vault if missing
        empty = Storage(entries=[])
        empty.save(VAULT_PATH)
    return Storage.load(VAULT_PATH)


def save_vault(vault: Storage) -> None:
    """Save plaintext vault."""
    vault.save(VAULT_PATH)


def timestamp() -> str:
    from datetime import datetime

    return datetime.now().strftime("%Y%m%d-%H%M%S")
