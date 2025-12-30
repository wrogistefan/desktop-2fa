"""CLI helper functions for Desktop 2FA."""

import shutil
import time
from pathlib import Path

from desktop_2fa.vault import Vault


def list_entries() -> None:
    """List all entries in the vault."""
    vault = load_vault()
    for entry in vault.entries:
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


def generate_code(issuer: str) -> None:
    """Generate and print the TOTP code for the given issuer.

    Args:
        issuer: The issuer name of the entry.
    """
    vault = load_vault()
    entry = vault.get_entry(issuer)

    from desktop_2fa.totp.generator import generate

    code = generate(
        secret=entry.secret,
        digits=entry.digits,
        period=entry.period,
        algorithm=entry.algorithm,
    )

    print(code)


def remove_entry(issuer: str) -> None:
    """Remove an entry from the vault by issuer.

    Args:
        issuer: The issuer name of the entry to remove.
    """
    vault = load_vault()
    vault.remove_entry(issuer)
    save_vault(vault)
    print(f"Removed entry: {issuer}")


def rename_entry(old_issuer: str, new_issuer: str) -> None:
    """Rename an entry's issuer from old_issuer to new_issuer.

    Args:
        old_issuer: The current issuer name.
        new_issuer: The new issuer name.
    """
    vault = load_vault()
    entry = vault.get_entry(old_issuer)
    entry.account_name = new_issuer
    entry.issuer = new_issuer

    save_vault(vault)
    print(f"Renamed '{old_issuer}' → '{new_issuer}'")


def export_vault(path: str) -> None:
    """Export the vault file to the specified path.

    Args:
        path: The destination file path.
    """
    src = Path(get_vault_path())
    dst = Path(path)

    if not src.exists():
        print("Vault does not exist.")
        return

    shutil.copy2(src, dst)
    print(f"Exported vault to: {dst}")


def import_vault(path: str) -> None:
    """Import the vault file from the specified path.

    Args:
        path: The source file path.
    """
    src = Path(path)
    dst = Path(get_vault_path())

    if not src.exists():
        print("Source file does not exist.")
        return

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"Imported vault from: {src}")


def backup_vault() -> None:
    """Create a backup of the vault file."""
    src = Path(get_vault_path())

    if not src.exists():
        print("Vault does not exist.")
        return

    backup_path = src.with_suffix(".backup.bin")
    shutil.copy2(src, backup_path)
    print(f"Backup created: {backup_path}")


def get_vault_path() -> str:
    """Get the default path for the vault file.

    Returns:
        The path to the vault file as a string.
    """
    return str(Path.home() / ".desktop-2fa" / "vault")


def load_vault() -> Vault:
    """Load the vault from the default path.

    Returns:
        The loaded Vault instance.
    """
    return Vault.load(get_vault_path())


def save_vault(vault: Vault) -> None:
    """Save the vault to the default path.

    Args:
        vault: The Vault instance to save.
    """
    path = Path(get_vault_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    vault.save(str(path))


def timestamp() -> str:
    """Get the current timestamp as a string.

    Returns:
        The current Unix timestamp as a string.
    """
    return str(int(time.time()))
