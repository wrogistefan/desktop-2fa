"""CLI command implementations for Desktop 2FA."""

from __future__ import annotations

from pathlib import Path

import typer

import desktop_2fa.cli.helpers as helpers
from desktop_2fa.vault import Vault
from desktop_2fa.vault.vault import (
    CorruptedVault,
    InvalidPassword,
    UnsupportedFormat,
    VaultIOError,
)


def _path() -> Path:
    return Path(helpers.get_vault_path())


def list_entries(ctx: typer.Context) -> None:
    path = _path()
    interactive = ctx.obj.get("interactive", False)
    if not path.exists():
        if interactive:
            helpers.print_warning("No vault found.")
            helpers.print_info("A new encrypted vault will be created.")
        password = helpers.get_password_for_vault(ctx, new_vault=True)
        vault = Vault()
        vault.save(path, password)
        if interactive:
            helpers.print_success("Vault created.")
            helpers.print_info("No entries found.")
    else:
        password = helpers.get_password_for_vault(ctx, new_vault=False)
        try:
            vault = Vault.load(path, password)
        except InvalidPassword:
            if interactive:
                helpers.print_error("Invalid vault password.")
            return
        except CorruptedVault:
            if interactive:
                helpers.print_error("Vault file is corrupted.")
            return
        except UnsupportedFormat:
            if interactive:
                helpers.print_error("Vault file format is unsupported.")
            return
        except VaultIOError:
            if interactive:
                helpers.print_error("Failed to access vault file.")
            return
        if vault.entries:
            helpers.print_entries_table(vault.entries)
        else:
            if interactive:
                helpers.print_info("No entries found.")


def add_entry(issuer: str, secret: str, ctx: typer.Context) -> None:
    path = _path()

    account_name = issuer  # Default account_name to issuer

    # Parse otpauth URL if provided
    if issuer.startswith("otpauth://"):
        try:
            parsed = helpers.parse_otpauth_url(issuer)
            issuer = parsed["issuer"]
            account_name = parsed["label"]
            secret = parsed["secret"]
        except ValueError as e:
            helpers.print_error(f"Invalid otpauth URL: {e}")
            return

    # Validate Base32 secret
    if not helpers.validate_base32(secret):
        helpers.print_error("Invalid secret: not valid Base32.")
        helpers.print_info("Example: ABCDEFGHIJKL2345")
        return

    if not path.exists():
        helpers.print_warning("No vault found.")
        helpers.print_info("A new encrypted vault will be created.")
        password = helpers.get_password_for_vault(ctx, new_vault=True)
        vault = Vault()
        vault.add_entry(issuer=issuer, account_name=account_name, secret=secret)
        vault.save(path, password)
        helpers.print_success("Vault created.")
        helpers.print_success(f"Entry added: {issuer}")
    else:
        password = helpers.get_password_for_vault(ctx, new_vault=False)
        try:
            vault = Vault.load(path, password)
            vault.add_entry(issuer=issuer, account_name=account_name, secret=secret)
            vault.save(path, password)
            helpers.print_success(f"Entry added: {issuer}")
        except InvalidPassword:
            helpers.print_error("Invalid vault password.")
        except CorruptedVault:
            helpers.print_error("Vault file is corrupted.")
        except UnsupportedFormat:
            helpers.print_error("Vault file format is unsupported.")
        except VaultIOError:
            helpers.print_error("Failed to access vault file.")


def generate_code(name: str, ctx: typer.Context) -> None:
    path = _path()
    if not path.exists():
        helpers.print_warning("No vault found.")
        helpers.print_info("Nothing to generate.")
        return
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
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
    except ValueError as e:
        if "not found" in str(e):
            raise
        helpers.print_error("Invalid vault password.")
    except InvalidPassword:
        helpers.print_error("Invalid vault password.")
    except CorruptedVault:
        helpers.print_error("Vault file is corrupted.")
    except UnsupportedFormat:
        helpers.print_error("Vault file format is unsupported.")
    except VaultIOError:
        helpers.print_error("Failed to access vault file.")


def remove_entry(name: str, ctx: typer.Context) -> None:
    path = _path()
    if not path.exists():
        helpers.print_warning("No vault found.")
        return
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
        vault = Vault.load(path, password)
        vault.remove_entry(name)
        vault.save(path, password)
        helpers.print_success(f"Removed entry: {name}")
    except ValueError as e:
        if "not found" in str(e):
            raise
        helpers.print_error("Invalid vault password.")
    except InvalidPassword:
        helpers.print_error("Invalid vault password.")
    except CorruptedVault:
        helpers.print_error("Vault file is corrupted.")
    except UnsupportedFormat:
        helpers.print_error("Vault file format is unsupported.")
    except VaultIOError:
        helpers.print_error("Failed to access vault file.")


def rename_entry(old: str, new: str, ctx: typer.Context) -> None:
    path = _path()
    if not path.exists():
        helpers.print_warning("No vault found.")
        return
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
        vault = Vault.load(path, password)
        entry = vault.get_entry(old)
        entry.account_name = new
        entry.issuer = new
        vault.save(path, password)
        helpers.print_success(f"Renamed '{old}' → '{new}'")
    except ValueError as e:
        if "not found" in str(e):
            raise
        helpers.print_error("Invalid vault password.")
    except InvalidPassword:
        helpers.print_error("Invalid vault password.")
    except CorruptedVault:
        helpers.print_error("Vault file is corrupted.")
    except UnsupportedFormat:
        helpers.print_error("Vault file format is unsupported.")
    except VaultIOError:
        helpers.print_error("Failed to access vault file.")


def export_vault(export_path: str, ctx: typer.Context) -> None:
    path = _path()
    if not path.exists():
        helpers.print_warning("No vault found.")
        return
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
        vault = Vault.load(path, password)
        vault.save(Path(export_path), password)
        helpers.print_success(f"Exported vault to: {export_path}")
    except InvalidPassword:
        helpers.print_error("Invalid vault password.")
    except CorruptedVault:
        helpers.print_error("Vault file is corrupted.")
    except UnsupportedFormat:
        helpers.print_error("Vault file format is unsupported.")
    except VaultIOError:
        helpers.print_error("Failed to access vault file.")


def import_vault(source: str, force: bool, ctx: typer.Context) -> None:
    path = _path()
    if path.exists() and not force:
        helpers.print_error(
            "Refusing to overwrite existing vault. Use --force to proceed."
        )
        raise typer.Exit(1)
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
        vault = Vault.load(Path(source), password)
        vault.save(path, password)
        helpers.print_success(f"Vault imported from {source}")
    except VaultIOError:
        raise
    except InvalidPassword:
        helpers.print_error("Invalid vault password.")
    except CorruptedVault:
        helpers.print_error("Source vault file is corrupted.")
    except UnsupportedFormat:
        helpers.print_error("Source vault file format is unsupported.")


def _get_backup_path(base_path: Path) -> Path:
    """Get the next available backup path with auto-suffixing."""
    backup_path = base_path.with_suffix(".backup.bin")
    if not backup_path.exists():
        return backup_path
    counter = 1
    while True:
        suffixed_path = base_path.with_suffix(f".backup-{counter}.bin")
        if not suffixed_path.exists():
            return suffixed_path
        counter += 1


def backup_vault(ctx: typer.Context) -> None:
    path = _path()
    if not path.exists():
        helpers.print_warning("No vault found.")
        return
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
        vault = Vault.load(path, password)
        backup_path = _get_backup_path(path)
        vault.save(backup_path, password)
        helpers.print_success(f"Backup created: {backup_path}")
    except InvalidPassword:
        helpers.print_error("Invalid vault password.")
    except CorruptedVault:
        helpers.print_error("Vault file is corrupted.")
    except UnsupportedFormat:
        helpers.print_error("Vault file format is unsupported.")
    except VaultIOError:
        helpers.print_error("Failed to access vault file.")


def init_vault(force: bool, ctx: typer.Context) -> None:
    """Initialize a new vault explicitly."""
    path = _path()
    if path.exists() and not force:
        helpers.print_info("Vault already exists.")
        helpers.print_info("Use --force to overwrite.")
        return

    if path.exists() and force:
        helpers.print_error("Existing vault will be overwritten.")

    password = helpers.get_password_for_vault(ctx, new_vault=True)
    vault = Vault()
    vault.save(path, password)
    helpers.print_success("Vault created.")
