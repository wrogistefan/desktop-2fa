"""CLI command implementations for Desktop 2FA."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from desktop_2fa.totp.generator import generate

from .helpers import get_vault_path, load_vault, save_vault


def list_entries() -> None:
    """List all entries in the vault."""
    vault = load_vault()
    if not vault.entries:
        print("Vault is empty.")
        return
    for entry in vault.entries:
        # Show name (issuer), because issuer can repeat
        print(f"- {entry.account_name} ({entry.issuer})")


def add_entry(issuer: str, secret: str) -> None:
    """Add a new entry to the vault.

    Args:
        issuer: The issuer name for the TOTP token.
        secret: The base32-encoded secret key.
    """
    vault = load_vault()
    vault.add_entry(issuer=issuer, account_name=issuer, secret=secret)
    save_vault(vault)
    print(f"Added entry: {issuer}")


def generate_code(name: str) -> None:
    """Generate and print the TOTP code for the given entry name.

    Args:
        name: The name of the entry in the vault.
    """
    vault = load_vault()
    entry = vault.get_entry(name)
    code = generate(
        secret=entry.secret,
        digits=entry.digits,
        period=entry.period,
        algorithm=entry.algorithm,
    )
    print(code)


def remove_entry(name: str) -> None:
    """Remove an entry from the vault by name.

    Args:
        name: The name of the entry to remove.
    """
    vault = load_vault()
    vault.remove_entry(name)
    save_vault(vault)
    print(f"Removed entry: {name}")


def rename_entry(old: str, new: str) -> None:
    """Rename an entry label from old to new.

    Issuer is not modified. Multiple entries may share the same issuer,
    but each entry name should be unique.

    Args:
        old: The current name of the entry.
        new: The new name for the entry.
    """
    vault = load_vault()
    entry = vault.get_entry(old)
    entry.account_name = new
    entry.issuer = new
    save_vault(vault)
    print(f"Renamed {old} → {new}")


def export_vault(path: str) -> None:
    """Export the vault to a JSON file.

    Args:
        path: The file path to export the vault to.
    """
    vault_path = get_vault_path()
    if not Path(vault_path).exists():
        print("Vault does not exist.")
        return
    vault = load_vault()
    data = json.loads(vault.data.model_dump_json())
    Path(path).write_text(json.dumps(data, indent=2))
    print(f"Vault exported to {path}")


def import_vault(path: str) -> None:
    """Import the vault from a JSON file, overwriting existing entries.

    Args:
        path: The file path to import the vault from.
    """
    if not Path(path).exists():
        print("Source file does not exist.")
        return
    data = json.loads(Path(path).read_text())
    vault = load_vault()
    vault.data.entries = []  # overwrite

    for entry in data["entries"]:
        # Assume JSON already has name / issuer / secret
        name = entry.get("name") or entry["issuer"]
        issuer = entry["issuer"]
        secret = entry["secret"]
        vault.add_entry(issuer=issuer, account_name=name, secret=secret)

    save_vault(vault)
    print(f"Vault imported from {path}")


def backup_vault() -> None:
    """Create a backup of the vault file."""
    vault_path = Path(get_vault_path())
    if not vault_path.exists():
        print("Vault does not exist.")
        return
    backup_path = vault_path.with_suffix(".backup.bin")
    shutil.copy2(vault_path, backup_path)
    print(f"Backup created: {backup_path}")
