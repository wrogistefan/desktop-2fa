from __future__ import annotations

import json
from pathlib import Path

from desktop_2fa.totp import generate_totp

from .helpers import VAULT_PATH, load_vault, save_vault, timestamp


def list_entries() -> None:
    vault = load_vault()
    if not vault.entries:
        print("Vault is empty.")
        return
    for entry in vault.entries:
        print(f"- {entry.issuer}")


def add_entry(issuer: str, secret: str) -> None:
    vault = load_vault()
    vault.add_entry(issuer=issuer, secret=secret)
    save_vault(vault)
    print(f"Added entry: {issuer}")


def generate_code(issuer: str) -> None:
    vault = load_vault()
    entry = vault.get_entry(issuer)
    code = generate_totp(entry.secret)
    print(code)


def remove_entry(issuer: str) -> None:
    vault = load_vault()
    vault.remove_entry(issuer)
    save_vault(vault)
    print(f"Removed entry: {issuer}")


def rename_entry(old: str, new: str) -> None:
    vault = load_vault()
    entry = vault.get_entry(old)
    entry.issuer = new
    save_vault(vault)
    print(f"Renamed {old} → {new}")


def export_vault(path: str) -> None:
    vault = load_vault()
    data = vault.to_json()
    Path(path).write_text(json.dumps(data, indent=2))
    print(f"Vault exported to {path}")


def import_vault(path: str) -> None:
    data = json.loads(Path(path).read_text())
    vault = load_vault()
    vault.entries = []  # overwrite
    for entry in data["entries"]:
        vault.add_entry(entry["issuer"], entry["secret"])
    save_vault(vault)
    print(f"Vault imported from {path}")


def backup_vault() -> None:
    backup_path = f"vault-backup-{timestamp()}.json"
    Path(VAULT_PATH).rename(backup_path)
    print(f"Backup created: {backup_path}")
