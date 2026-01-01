"""CLI helper functions for Desktop 2FA."""

import time
from pathlib import Path

import typer

from desktop_2fa.vault import Vault


def list_entries(path: Path, password: str) -> None:
    """List all entries in the vault."""
    vault = Vault.load(path, password)
    for entry in vault.entries:
        print(f"- {entry.account_name} ({entry.issuer})")


def add_entry(
    path: Path, issuer: str, account: str, secret: str, password: str
) -> None:
    """Add a new entry to the vault."""
    vault = Vault.load(path, password)
    vault.add_entry(issuer=issuer, account_name=account, secret=secret)
    vault.save(path, password)
    print(f"Added entry: {issuer}")


def generate_code(path: Path, name: str, password: str) -> None:
    """Generate and print the TOTP code for the given issuer."""
    vault = Vault.load(path, password)
    entry = vault.get_entry(name)

    from desktop_2fa.totp.generator import generate

    code = generate(
        secret=entry.secret,
        digits=entry.digits,
        period=entry.period,
        algorithm=entry.algorithm,
    )

    print(code)


def remove_entry(path: Path, name: str, password: str) -> None:
    """Remove an entry from the vault."""
    vault = Vault.load(path, password)
    vault.remove_entry(name)
    vault.save(path, password)
    print(f"Removed entry: {name}")


def rename_entry(path: Path, old: str, new: str, password: str) -> None:
    """Rename an entry."""
    vault = Vault.load(path, password)
    entry = vault.get_entry(old)
    entry.account_name = new
    entry.issuer = new

    vault.save(path, password)
    print(f"Renamed '{old}' → '{new}'")


def export_vault(path: Path, export_path: Path, password: str) -> None:
    """Export the vault file."""
    vault = Vault.load(path, password)
    vault.save(export_path, password)
    print(f"Exported vault to: {export_path}")


def import_vault(path: Path, import_path: Path, password: str) -> None:
    """Import the vault file."""
    vault = Vault.load(import_path, password=password)
    vault.save(path, password)
    print("Vault imported from")


def backup_vault(path: Path, backup_path: Path, password: str) -> None:
    """Create a backup of the vault file."""
    vault = Vault.load(path, password)
    vault.save(backup_path, password)
    print("Backup created:")


def get_vault_path() -> str:
    """Get the default path for the vault file."""
    return str(Path.home() / ".desktop-2fa" / "vault")


def load_vault(path: Path, password: str) -> Vault:
    """Load the vault from the specified path."""
    try:
        return Vault.load(path, password)
    except Exception as e:
        raise Exception(f"Failed to load vault: {e}") from e


def save_vault(path: Path, vault: Vault, password: str) -> None:
    """Save the vault to the specified path."""
    vault.save(path, password)


def get_password_for_vault(ctx: typer.Context, new_vault: bool = False) -> str:
    """Get the password for vault operations."""
    password = ctx.obj.get("password")
    password_file = ctx.obj.get("password_file")
    interactive = ctx.obj.get("interactive")

    # Both flags provided
    if password and password_file:
        print("Error: Cannot specify both --password and --password-file")
        raise typer.Exit(1)

    # Direct password
    if password:
        return password  # type: ignore[no-any-return]

    # Password from file
    if password_file:
        try:
            with open(password_file, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            print(f"Error: Password file '{password_file}' not found")
            raise typer.Exit(1)
        except Exception as e:
            print(f"Error reading password file: {e}")
            raise typer.Exit(1)

    # No password provided
    if not interactive:
        print("Error: Password not provided and not running in interactive mode")
        raise typer.Exit(1)

    # Interactive mode → prompt
    pwd = typer.prompt("Enter vault password", hide_input=True)
    if new_vault:
        confirm = typer.prompt("Confirm vault password", hide_input=True)
        if pwd != confirm:
            print("Passwords do not match. Please try again.")
            raise typer.Exit(1)
    return pwd  # type: ignore[no-any-return]


def timestamp() -> str:
    return str(int(time.time()))
