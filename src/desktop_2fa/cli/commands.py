from __future__ import annotations

import json
import shutil
from pathlib import Path

from desktop_2fa.totp import generate_totp

from .helpers import get_vault_path, load_vault, save_vault


def list_entries() -> None:
    vault = load_vault()
    if not vault.entries:
        print("Vault is empty.")
        return
    for entry in vault.entries:
        # pokazujemy name (issuer), bo issuer może się powtarzać
        print(f"- {entry.name} ({entry.issuer})")


def add_entry(issuer: str, secret: str) -> None:
    vault = load_vault()
    vault.add_entry(name=issuer, issuer=issuer, secret=secret)
    save_vault(vault)
    print(f"Added entry: {issuer}")


def generate_code(name: str) -> None:
    vault = load_vault()
    entry = vault.get_entry(name)
    code = generate_totp(entry.secret)
    print(code)


def remove_entry(name: str) -> None:
    vault = load_vault()
    vault.remove_entry(name)
    save_vault(vault)
    print(f"Removed entry: {name}")


def rename_entry(old: str, new: str) -> None:
    """
    Rename an entry label from OLD to NEW.

    Issuer is not modified. Multiple entries may share the same issuer,
    but each entry name should be unique.
    """
    vault = load_vault()
    entry = vault.get_entry(old)
    entry.name = new
    entry.issuer = new
    save_vault(vault)
    print(f"Renamed {old} → {new}")


def export_vault(path: str) -> None:
    vault_path = get_vault_path()
    if not Path(vault_path).exists():
        print("Vault does not exist.")
        return
    vault = load_vault()
    data = vault.to_json()
    Path(path).write_text(json.dumps(data, indent=2))
    print(f"Vault exported to {path}")


def import_vault(path: str) -> None:
    if not Path(path).exists():
        print("Source file does not exist.")
        return
    data = json.loads(Path(path).read_text())
    vault = load_vault()
    vault.data.entries = []  # overwrite

    for entry in data["entries"]:
        # zakładamy, że JSON ma już name / issuer / secret
        name = entry.get("name") or entry["issuer"]
        issuer = entry["issuer"]
        secret = entry["secret"]
        vault.add_entry(name=name, issuer=issuer, secret=secret)

    save_vault(vault)
    print(f"Vault imported from {path}")


def backup_vault() -> None:
    vault_path = Path(get_vault_path())
    if not vault_path.exists():
        print("Vault does not exist.")
        return
    backup_path = vault_path.with_suffix(".backup.bin")
    shutil.copy2(vault_path, backup_path)
    print(f"Backup created: {backup_path}")
