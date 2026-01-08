"""CLI command implementations for Desktop 2FA."""

from __future__ import annotations

from pathlib import Path

import typer

import desktop_2fa.cli.helpers as helpers
from desktop_2fa.vault import Vault
from desktop_2fa.vault.vault import (
    CorruptedVault,
    InvalidPassword,
    PermissionDenied,
    UnsupportedFormat,
    VaultIOError,
    VaultNotFound,
)


def _path() -> Path:
    """Get the path to the vault file.

    Returns:
        Path to the vault file.
    """
    return Path(helpers.get_vault_path())


def _vault_exists(path: Path) -> bool | None:
    """Check if vault file exists and is accessible.

    This safely checks vault existence without triggering PermissionError
    from path.exists(), which raises when file exists but cannot be accessed.

    Args:
        path: Path to the vault file.

    Returns:
        True if vault exists and is readable,
        False if file does not exist,
        None if permission denied (caller should handle this case).
    """
    try:
        with open(path, "rb"):
            return True
    except FileNotFoundError:
        return False
    except PermissionError:
        # Permission denied - file may exist but we can't access it
        return None
    except OSError:
        # Other I/O errors (disk full, etc.) - re-raise for proper handling
        raise


def add_entry_interactive(
    name: str, issuer: str, secret: str, ctx: typer.Context
) -> None:
    """Add an entry to the vault in interactive mode.

    Args:
        name: The unique account name.
        issuer: The issuer name or otpauth:// URL.
        secret: The Base32-encoded TOTP secret.
        ctx: Typer context with password options.
    """
    path = _path()

    # Validate Base32 secret
    if not helpers.validate_base32(secret):
        helpers.print_error("Invalid secret: not valid Base32.")
        helpers.print_info("Example: ABCDEFGHIJKL2345")
        return

    # DEF-02: Use safe vault existence check (avoids PermissionError from path.exists())
    try:
        vault_exists = _vault_exists(path)
    except OSError:
        # DEF-02: I/O error during existence check
        helpers.print_error("Failed to access vault file.")
        return

    # DEF-02: Handle permission denied during existence check
    if vault_exists is None:
        helpers.print_error("Error: Cannot access vault directory (permission denied).")
        return

    if not vault_exists:
        helpers.print_warning("No vault found.")
        helpers.print_info("A new encrypted vault will be created.")
        password = helpers.get_password_for_vault(ctx, new_vault=True)
        vault = Vault()
        vault.add_entry(name=name, issuer=issuer, secret=secret)
        try:
            vault.save(path, password)
        except PermissionDenied:
            helpers.print_error("Cannot access vault directory (permission denied).")
            return
        print(f"Vault created at {path}")
        print(f"Entry added: {name}")
    else:
        password = helpers.get_password_for_vault(ctx, new_vault=False)
        try:
            vault = Vault.load(path, password)
            vault.add_entry(name=name, issuer=issuer, secret=secret)
            vault.save(path, password)
            helpers.print_success(f"Entry added: {name}")
        except ValueError as e:
            if "already exists" in str(e):
                helpers.print_error(str(e))
            else:
                helpers.print_error("Invalid vault password.")
        except InvalidPassword:
            helpers.print_error("Invalid vault password.")
        except CorruptedVault:
            helpers.print_error("Vault file is corrupted.")
        except UnsupportedFormat:
            helpers.print_error("Vault file format is unsupported.")
        except VaultIOError:
            helpers.print_error("Failed to access vault file.")


def list_entries(ctx: typer.Context) -> None:
    """List all entries in the vault.

    Args:
        ctx: Typer context with password options.
    """
    path = _path()
    interactive = ctx.obj.get("interactive", False)

    # DEF-02: Use safe vault existence check (avoids PermissionError from path.exists())
    try:
        vault_exists = _vault_exists(path)
    except OSError:
        # DEF-02: I/O error during existence check
        helpers.print_error("Failed to access vault file.")
        return

    # DEF-02: Handle permission denied during existence check
    if vault_exists is None:
        helpers.print_error("Error: Cannot access vault directory (permission denied).")
        return

    if not vault_exists:
        helpers.print_warning("No vault found.")
        helpers.print_info("A new encrypted vault will be created.")
        password = helpers.get_password_for_vault(ctx, new_vault=True)
        vault = Vault()
        try:
            vault.save(path, password)
        except PermissionDenied:
            helpers.print_error("Cannot access vault directory (permission denied).")
            return
        print(f"Vault created at {path}")
        print("No entries found.")
    else:
        password = helpers.get_password_for_vault(ctx, new_vault=False)
        try:
            vault = Vault.load(path, password)
        except PermissionDenied:
            helpers.print_error(
                "Error: Cannot access vault directory (permission denied)."
            )
            return
        except VaultNotFound:
            helpers.print_warning("No vault found.")
            helpers.print_info("A new encrypted vault will be created.")
            password = helpers.get_password_for_vault(ctx, new_vault=True)
            vault = Vault()
            try:
                vault.save(path, password)
            except PermissionDenied:
                helpers.print_error(
                    "Cannot access vault directory (permission denied)."
                )
                return
            print(f"Vault created at {path}")
            print("No entries found.")
            return
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


def add_entry(name: str, issuer: str, secret: str, ctx: typer.Context) -> None:
    """Add an entry to the vault.

    Args:
        name: The unique account name.
        issuer: The issuer name or otpauth:// URL.
        secret: The Base32-encoded TOTP secret.
        ctx: Typer context with password options.
    """
    path = _path()

    # Parse otpauth URL if provided
    if issuer.startswith("otpauth://"):
        try:
            parsed = helpers.parse_otpauth_url(issuer)
            issuer = parsed["issuer"]
            name = parsed["label"]
            secret = parsed["secret"]
        except ValueError as e:
            helpers.print_error(f"Invalid otpauth URL: {e}")
            return

    # Validate Base32 secret
    if not helpers.validate_base32(secret):
        helpers.print_error("Invalid secret: not valid Base32.")
        helpers.print_info("Example: ABCDEFGHIJKL2345")
        return

    # DEF-02: Use safe vault existence check (avoids PermissionError from path.exists())
    try:
        vault_exists = _vault_exists(path)
    except OSError:
        # DEF-02: I/O error during existence check
        helpers.print_error("Failed to access vault file.")
        return

    # DEF-02: Handle permission denied during existence check
    if vault_exists is None:
        helpers.print_error("Error: Cannot access vault directory (permission denied).")
        return

    if not vault_exists:
        helpers.print_warning("No vault found.")
        helpers.print_info("A new encrypted vault will be created.")
        password = helpers.get_password_for_vault(ctx, new_vault=True)
        vault = Vault()
        vault.add_entry(name=name, issuer=issuer, secret=secret)
        try:
            vault.save(path, password)
        except PermissionDenied:
            helpers.print_error("Cannot access vault directory (permission denied).")
            return
        print(f"Vault created at {path}")
        print(f"Entry added: {name}")
    else:
        password = helpers.get_password_for_vault(ctx, new_vault=False)
        try:
            vault = Vault.load(path, password)
            vault.add_entry(name=name, issuer=issuer, secret=secret)
            vault.save(path, password)
            helpers.print_success(f"Entry added: {name}")
        except PermissionDenied:
            helpers.print_error(
                "Error: Cannot access vault directory (permission denied)."
            )
        except VaultNotFound:
            helpers.print_warning("No vault found.")
            helpers.print_info("A new encrypted vault will be created.")
            password = helpers.get_password_for_vault(ctx, new_vault=True)
            vault = Vault()
            vault.add_entry(name=name, issuer=issuer, secret=secret)
            try:
                vault.save(path, password)
            except PermissionDenied:
                helpers.print_error(
                    "Cannot access vault directory (permission denied)."
                )
                return
            print(f"Vault created at {path}")
            # CodeQL [py/clear-text-logging-sensitive-data]: false positive, secret is never logged
            print(f"Entry added: {name}")
        except ValueError as e:
            if "already exists" in str(e):
                helpers.print_error(str(e))
            else:
                helpers.print_error("Invalid vault password.")
        except InvalidPassword:
            helpers.print_error("Invalid vault password.")
        except CorruptedVault:
            helpers.print_error("Vault file is corrupted.")
        except UnsupportedFormat:
            helpers.print_error("Vault file format is unsupported.")
        except VaultIOError:
            helpers.print_error("Failed to access vault file.")


def generate_code(name: str, ctx: typer.Context) -> None:
    """Generate and print the TOTP code for the given entry.

    Args:
        name: The name of the entry to generate code for.
        ctx: Typer context with password options.
    """
    path = _path()
    try:
        vault_exists = _vault_exists(path)
    except OSError:
        # DEF-02: I/O error during existence check
        helpers.print_error("Failed to access vault file.")
        return

    # DEF-02: Handle permission denied during existence check
    if vault_exists is None:
        helpers.print_error("Error: Cannot access vault directory (permission denied).")
        return

    if not vault_exists:
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
    except PermissionDenied:
        helpers.print_error("Error: Cannot access vault directory (permission denied).")
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
    """Remove an entry from the vault.

    Args:
        name: The name of the entry to remove.
        ctx: Typer context with password options.
    """
    path = _path()
    try:
        vault_exists = _vault_exists(path)
    except OSError:
        # DEF-02: I/O error during existence check
        helpers.print_error("Failed to access vault file.")
        return

    # DEF-02: Handle permission denied during existence check
    if vault_exists is None:
        helpers.print_error("Error: Cannot access vault directory (permission denied).")
        return

    if not vault_exists:
        helpers.print_warning("No vault found.")
        return
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
        vault = Vault.load(path, password)
        vault.remove_entry(name)
        vault.save(path, password)
        helpers.print_success(f"Removed entry: {name}")
    except PermissionDenied:
        helpers.print_error("Error: Cannot access vault directory (permission denied).")
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
    """Rename an entry in the vault.

    Args:
        old: The current name of the entry.
        new: The new name for the entry.
        ctx: Typer context with password options.
    """
    path = _path()
    try:
        vault_exists = _vault_exists(path)
    except OSError:
        # DEF-02: I/O error during existence check
        helpers.print_error("Failed to access vault file.")
        return

    # DEF-02: Handle permission denied during existence check
    if vault_exists is None:
        helpers.print_error("Error: Cannot access vault directory (permission denied).")
        return

    if not vault_exists:
        helpers.print_warning("No vault found.")
        return
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
        vault = Vault.load(path, password)
        # Check for duplicates before renaming
        old_matches = vault.find_entries(old)
        if len(old_matches) > 1:
            print(
                f"Multiple entries named '{old}' exist. Operation aborted. Resolve duplicates first."
            )
            return
        entry = vault.get_entry(old)
        entry.account_name = new
        entry.issuer = new
        vault.save(path, password)
        helpers.print_success(f"Renamed '{old}' → '{new}'")
    except PermissionDenied:
        helpers.print_error("Error: Cannot access vault directory (permission denied).")
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
    """Export the vault to a new file.

    Args:
        export_path: Path where the vault will be exported.
        ctx: Typer context with password options.
    """
    path = _path()
    try:
        vault_exists = _vault_exists(path)
    except OSError:
        # DEF-02: I/O error during existence check
        helpers.print_error("Failed to access vault file.")
        return

    # DEF-02: Handle permission denied during existence check
    if vault_exists is None:
        helpers.print_error("Error: Cannot access vault directory (permission denied).")
        return

    if not vault_exists:
        helpers.print_warning("No vault found.")
        return
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
        vault = Vault.load(path, password)
        vault.save(Path(export_path), password)
        helpers.print_success(f"Exported vault to: {export_path}")
    except PermissionDenied:
        helpers.print_error("Error: Cannot access vault directory (permission denied).")
    except InvalidPassword:
        helpers.print_error("Invalid vault password.")
    except CorruptedVault:
        helpers.print_error("Vault file is corrupted.")
    except UnsupportedFormat:
        helpers.print_error("Vault file format is unsupported.")
    except VaultIOError:
        helpers.print_error("Failed to access vault file.")


def import_vault(source: str, force: bool, ctx: typer.Context) -> None:
    """Import a vault from a source file.

    Args:
        source: Path to the source vault file.
        force: Whether to overwrite existing vault.
        ctx: Typer context with password options.
    """
    path = _path()
    # DEF-02: Use safe vault existence check (avoids PermissionError from path.exists())
    try:
        vault_exists = _vault_exists(path)
    except OSError:
        # DEF-02: I/O error during existence check
        helpers.print_error("Failed to access vault file.")
        return

    # DEF-02: Handle permission denied during existence check
    if vault_exists is None:
        helpers.print_error("Error: Cannot access vault directory (permission denied).")
        return

    if vault_exists and not force:
        helpers.print_error(
            "Refusing to overwrite existing vault. Use --force to proceed."
        )
        raise typer.Exit(1)
    if vault_exists and force:
        helpers.print_error("Existing vault will be overwritten.")
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
    """Get the next available backup path for the vault.

    Args:
        base_path: The original vault path.

    Returns:
        Path for the backup file.
    """
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
    """Create a backup of the vault.

    Args:
        ctx: Typer context with password options.
    """
    path = _path()
    try:
        vault_exists = _vault_exists(path)
    except OSError:
        # DEF-02: I/O error during existence check
        helpers.print_error("Failed to access vault file.")
        return

    # DEF-02: Handle permission denied during existence check
    if vault_exists is None:
        helpers.print_error("Error: Cannot access vault directory (permission denied).")
        return

    if not vault_exists:
        helpers.print_warning("No vault found.")
        return
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
        vault = Vault.load(path, password)
        backup_path = _get_backup_path(path)
        vault.save(backup_path, password)
        helpers.print_success(f"Backup created: {backup_path}")
    except PermissionDenied:
        helpers.print_error("Error: Cannot access vault directory (permission denied).")
    except InvalidPassword:
        helpers.print_error("Invalid vault password.")
    except CorruptedVault:
        helpers.print_error("Vault file is corrupted.")
    except UnsupportedFormat:
        helpers.print_error("Vault file format is unsupported.")
    except VaultIOError:
        helpers.print_error("Failed to access vault file.")


def init_vault(force: bool, ctx: typer.Context) -> None:
    """Initialize a new encrypted vault.

    Args:
        force: Whether to overwrite existing vault.
        ctx: Typer context with password options.
    """
    path = _path()
    # DEF-02: Use safe vault existence check (avoids PermissionError from path.exists())
    try:
        vault_exists = _vault_exists(path)
    except OSError:
        # DEF-02: I/O error during existence check
        helpers.print_error("Failed to access vault file.")
        return

    # DEF-02: Handle permission denied during existence check
    if vault_exists is None:
        helpers.print_error("Error: Cannot access vault directory (permission denied).")
        return

    if vault_exists and not force:
        helpers.print_info("Vault already exists.")
        helpers.print_info("Use --force to overwrite.")
        return
    if vault_exists and force:
        helpers.print_error("Existing vault will be overwritten.")

    # DEF-02: Check for permission issues before trying to create vault
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        helpers.print_error("Error: Cannot access vault directory (permission denied).")
        return

    password = helpers.get_password_for_vault(ctx, new_vault=True)
    vault = Vault()
    try:
        vault.save(path, password)
        print(f"Vault created at {path}")
    except PermissionDenied:
        helpers.print_error("Error: Cannot access vault directory (permission denied).")
    except VaultIOError:
        helpers.print_error("Failed to create vault file.")
