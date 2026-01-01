"""CLI command implementations for Desktop 2FA."""

from __future__ import annotations

from pathlib import Path

import typer

import desktop_2fa.cli.helpers as helpers
from desktop_2fa.vault import Vault


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
        except Exception:
            if interactive:
                print("Invalid vault password.")
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
        except Exception:
            if interactive:
                print("Invalid vault password.")


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
    except Exception:
        if interactive:
            print("Invalid vault password.")


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
    except Exception:
        if interactive:
            print("Invalid vault password.")


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
    except Exception:
        if interactive:
            print("Invalid vault password.")


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
    except Exception:
        if interactive:
            print("Invalid vault password.")


def import_vault(source: str, ctx: typer.Context) -> None:
    path = _path()
    interactive = ctx.obj.get("interactive", False)
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
        vault = Vault.load(Path(source), password)
        vault.save(path, password)
        print("Vault imported from")
    except FileNotFoundError:
        raise
    except Exception:
        if interactive:
            print("Invalid vault password.")


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
        backup_path = path.with_suffix(".backup.bin")
        vault.save(backup_path, password)
        print("Backup created:")
    except Exception:
        if interactive:
            print("Invalid vault password.")
