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
            print("No vault found.")
            print("A new encrypted vault will be created.")
        password = helpers.get_password_for_vault(ctx, new_vault=True)
        vault = Vault()
        vault.save(path, password)
        if interactive:
            print("Vault created.")
            print("No entries found.")
    else:
        password = helpers.get_password_for_vault(ctx, new_vault=False)
        try:
            vault = Vault.load(path, password)
        except InvalidPassword:
            if interactive:
                print("Invalid vault password.")
            return
        except CorruptedVault:
            if interactive:
                print("Vault file is corrupted.")
            return
        except UnsupportedFormat:
            if interactive:
                print("Vault file format is unsupported.")
            return
        except VaultIOError:
            if interactive:
                print("Failed to access vault file.")
            return
        if vault.entries:
            for entry in vault.entries:
                print(f"- {entry.account_name} ({entry.issuer})")
        else:
            if interactive:
                print("No entries found.")


def add_entry(issuer: str, secret: str, ctx: typer.Context) -> None:
    path = _path()
    interactive = ctx.obj.get("interactive", False)
    if not path.exists():
        if interactive:
            print("No vault found.")
            print("A new encrypted vault will be created.")
        password = helpers.get_password_for_vault(ctx, new_vault=True)
        vault = Vault()
        vault.add_entry(issuer=issuer, account_name=issuer, secret=secret)
        vault.save(path, password)
        if interactive:
            print("Vault created.")
        print(f"Entry added: {issuer}")
    else:
        password = helpers.get_password_for_vault(ctx, new_vault=False)
        try:
            vault = Vault.load(path, password)
            vault.add_entry(issuer=issuer, account_name=issuer, secret=secret)
            vault.save(path, password)
            print(f"Entry added: {issuer}")
        except InvalidPassword:
            if interactive:
                print("Invalid vault password.")
        except CorruptedVault:
            if interactive:
                print("Vault file is corrupted.")
        except UnsupportedFormat:
            if interactive:
                print("Vault file format is unsupported.")
        except VaultIOError:
            if interactive:
                print("Failed to access vault file.")


def generate_code(name: str, ctx: typer.Context) -> None:
    path = _path()
    interactive = ctx.obj.get("interactive", False)
    if not path.exists():
        if interactive:
            print("No vault found.")
            print("Nothing to generate.")
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
        if interactive:
            print("Invalid vault password.")
    except InvalidPassword:
        if interactive:
            print("Invalid vault password.")
    except CorruptedVault:
        if interactive:
            print("Vault file is corrupted.")
    except UnsupportedFormat:
        if interactive:
            print("Vault file format is unsupported.")
    except VaultIOError:
        if interactive:
            print("Failed to access vault file.")


def remove_entry(name: str, ctx: typer.Context) -> None:
    path = _path()
    interactive = ctx.obj.get("interactive", False)
    if not path.exists():
        if interactive:
            print("No vault found.")
        return
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
        vault = Vault.load(path, password)
        vault.remove_entry(name)
        vault.save(path, password)
        print(f"Removed entry: {name}")
    except ValueError as e:
        if "not found" in str(e):
            raise
        if interactive:
            print("Invalid vault password.")
    except InvalidPassword:
        if interactive:
            print("Invalid vault password.")
    except CorruptedVault:
        if interactive:
            print("Vault file is corrupted.")
    except UnsupportedFormat:
        if interactive:
            print("Vault file format is unsupported.")
    except VaultIOError:
        if interactive:
            print("Failed to access vault file.")


def rename_entry(old: str, new: str, ctx: typer.Context) -> None:
    path = _path()
    interactive = ctx.obj.get("interactive", False)
    if not path.exists():
        if interactive:
            print("No vault found.")
        return
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
        vault = Vault.load(path, password)
        entry = vault.get_entry(old)
        entry.account_name = new
        entry.issuer = new
        vault.save(path, password)
        print(f"Renamed '{old}' → '{new}'")
    except ValueError as e:
        if "not found" in str(e):
            raise
        if interactive:
            print("Invalid vault password.")
    except InvalidPassword:
        if interactive:
            print("Invalid vault password.")
    except CorruptedVault:
        if interactive:
            print("Vault file is corrupted.")
    except UnsupportedFormat:
        if interactive:
            print("Vault file format is unsupported.")
    except VaultIOError:
        if interactive:
            print("Failed to access vault file.")


def export_vault(export_path: str, ctx: typer.Context) -> None:
    path = _path()
    interactive = ctx.obj.get("interactive", False)
    if not path.exists():
        if interactive:
            print("No vault found.")
        return
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
        vault = Vault.load(path, password)
        vault.save(Path(export_path), password)
        print(f"Exported vault to: {export_path}")
    except InvalidPassword:
        if interactive:
            print("Invalid vault password.")
    except CorruptedVault:
        if interactive:
            print("Vault file is corrupted.")
    except UnsupportedFormat:
        if interactive:
            print("Vault file format is unsupported.")
    except VaultIOError:
        if interactive:
            print("Failed to access vault file.")


def import_vault(source: str, force: bool, ctx: typer.Context) -> None:
    path = _path()
    interactive = ctx.obj.get("interactive", False)
    if path.exists() and not force:
        print("Refusing to overwrite existing vault. Use --force to proceed.")
        raise typer.Exit(1)
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
        vault = Vault.load(Path(source), password)
        vault.save(path, password)
        print("Vault imported from")
    except VaultIOError:
        raise
    except InvalidPassword:
        if interactive:
            print("Invalid vault password.")
    except CorruptedVault:
        if interactive:
            print("Source vault file is corrupted.")
    except UnsupportedFormat:
        if interactive:
            print("Source vault file format is unsupported.")


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
    interactive = ctx.obj.get("interactive", False)
    if not path.exists():
        if interactive:
            print("No vault found.")
        return
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
        vault = Vault.load(path, password)
        backup_path = _get_backup_path(path)
        vault.save(backup_path, password)
        print("Backup created:")
    except InvalidPassword:
        if interactive:
            print("Invalid vault password.")
    except CorruptedVault:
        if interactive:
            print("Vault file is corrupted.")
    except UnsupportedFormat:
        if interactive:
            print("Vault file format is unsupported.")
    except VaultIOError:
        if interactive:
            print("Failed to access vault file.")
