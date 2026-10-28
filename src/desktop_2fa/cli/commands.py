"""CLI command implementations for Desktop 2FA."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import typer

import desktop_2fa.cli.helpers as helpers
from desktop_2fa.constants import ExitCode
from desktop_2fa.utils.base32 import InvalidSecret, normalize_base32
from desktop_2fa.vault import Vault
from desktop_2fa.vault.password_strength import evaluate_password_strength
from desktop_2fa.vault.vault import (
    AmbiguousEntry,
    CorruptedVault,
    EntryRenameError,
    InvalidPassword,
    PermissionDenied,
    UnsupportedFormat,
    VaultIOError,
    VaultNotFound,
    VaultValidationError,
)


def _exit_with_error(
    code: int, err_id: str, message: str, json_mode: bool, quiet: bool
) -> None:
    """Print error message in appropriate format and exit with code.

    Args:
        code: Exit code.
        err_id: Error identifier for JSON mode.
        message: Human-readable error message.
        json_mode: Whether to output in JSON format.
        quiet: Whether to suppress output.
    """
    if json_mode:
        print(json.dumps({"error": err_id, "message": message}))
    elif not quiet:
        helpers.print_error(message)
    sys.exit(code)


def _handle_clipboard(
    code: str, copy: bool, copy_only: bool, json_mode: bool, quiet: bool
) -> bool:
    """Handle clipboard operations and return success status.

    Args:
        code: The TOTP code to copy.
        copy: Whether to copy and print.
        copy_only: Whether to copy without printing.
        json_mode: Whether output is in JSON mode.
        quiet: Whether to suppress output.

    Returns:
        True if clipboard operation succeeded, False otherwise.
        Exits with error code 5 if clipboard fails and copy_only is True.
    """
    from .clipboard import ClipboardError, copy_to_clipboard

    if copy or copy_only:
        try:
            copy_to_clipboard(code)
            return True
        except ClipboardError:
            if json_mode:
                print(
                    json.dumps(
                        {
                            "error": "clipboard_unavailable",
                            "message": "Clipboard not available on this system.",
                        }
                    )
                )
                sys.exit(5)
            elif not quiet:
                helpers.print_warning("Clipboard not available on this system.")
            if copy_only:
                sys.exit(5)
            return False
    return True


def _path(ctx: typer.Context) -> Path:
    """Get the path to the vault file.

    Returns:
        Path to the vault file.
    """
    vault_path = ctx.obj.get("vault_path")
    if vault_path is None:
        vault_path = helpers.get_vault_path()
    return Path(vault_path)


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
    fd: int | None = None
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
        return True
    except FileNotFoundError:
        return False
    except PermissionError:
        # Permission denied - file may exist but we can't access it
        return None
    except OSError:
        # Other I/O errors (disk full, etc.) - re-raise for proper handling
        raise
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def _prepare_add(name: str, issuer: str, secret: str) -> helpers.ParsedOtpauth:
    if issuer.startswith("otpauth://"):
        try:
            if secret:
                raise ValueError("Do not combine an otpauth URL with a separate secret")
            return helpers.parse_otpauth_url(issuer)
        except ValueError as e:
            helpers.print_error(f"Invalid otpauth URL: {e}")
            raise typer.Exit(ExitCode.VALIDATION_ERROR) from e
    try:
        secret = normalize_base32(secret)
    except InvalidSecret:
        helpers.print_error("Invalid secret: not valid Base32.")
        helpers.print_info(
            "A non-empty Base32 key is required. Example: ABCDEFGHIJKL2345"
        )
        raise typer.Exit(ExitCode.VALIDATION_ERROR) from None
    return {
        "label": name,
        "issuer": issuer,
        "secret": secret,
        "algorithm": "SHA1",
        "digits": 6,
        "period": 30,
    }


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
    path = _path(ctx)
    parsed = _prepare_add(name, issuer, secret)
    name, issuer, secret = parsed["label"], parsed["issuer"], parsed["secret"]
    parameters: helpers.TotpParameters = {
        "algorithm": parsed["algorithm"],
        "digits": parsed["digits"],
        "period": parsed["period"],
    }

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
        vault.add_entry(name=name, issuer=issuer, secret=secret, **parameters)
        try:
            vault.save(path, password)
        except VaultValidationError as e:
            helpers.print_error(str(e))
            raise typer.Exit(ExitCode.VALIDATION_ERROR) from None
        except PermissionDenied:
            helpers.print_error("Cannot access vault directory (permission denied).")
            return
        print(f"Vault created at {path}")
        print(f"Entry added: {name}")
    else:
        password = helpers.get_password_for_vault(ctx, new_vault=False)
        try:
            vault = Vault.load(path, password)
            vault.add_entry(name=name, issuer=issuer, secret=secret, **parameters)
            vault.save(path, password)
            helpers.print_success(f"Entry added: {name}")
        except VaultValidationError as e:
            helpers.print_error(str(e))
            raise typer.Exit(ExitCode.VALIDATION_ERROR) from None
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


def list_entries(ctx: typer.Context, *, show_indices: bool = False) -> None:
    """List all entries in the vault.

    Args:
        ctx: Typer context with password options.
    """
    path = _path(ctx)
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
        except VaultValidationError as e:
            helpers.print_error(str(e))
            raise typer.Exit(ExitCode.VALIDATION_ERROR) from None
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
            except VaultValidationError as e:
                helpers.print_error(str(e))
                raise typer.Exit(ExitCode.VALIDATION_ERROR) from None
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
            helpers.print_entries_table(vault.entries, show_indices=show_indices)
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
    path = _path(ctx)

    parsed = _prepare_add(name, issuer, secret)
    name, issuer, secret = parsed["label"], parsed["issuer"], parsed["secret"]
    parameters: helpers.TotpParameters = {
        "algorithm": parsed["algorithm"],
        "digits": parsed["digits"],
        "period": parsed["period"],
    }

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
        vault.add_entry(name=name, issuer=issuer, secret=secret, **parameters)
        try:
            vault.save(path, password)
        except VaultValidationError as e:
            helpers.print_error(str(e))
            raise typer.Exit(ExitCode.VALIDATION_ERROR) from None
        except PermissionDenied:
            helpers.print_error("Cannot access vault directory (permission denied).")
            return
        print(f"Vault created at {path}")
        print(f"Entry added: {name}")
    else:
        password = helpers.get_password_for_vault(ctx, new_vault=False)
        try:
            vault = Vault.load(path, password)
            vault.add_entry(name=name, issuer=issuer, secret=secret, **parameters)
            vault.save(path, password)
            helpers.print_success(f"Entry added: {name}")
        except VaultValidationError as e:
            helpers.print_error(str(e))
            raise typer.Exit(ExitCode.VALIDATION_ERROR) from None
        except PermissionDenied:
            helpers.print_error(
                "Error: Cannot access vault directory (permission denied)."
            )
        except VaultNotFound:
            helpers.print_warning("No vault found.")
            helpers.print_info("A new encrypted vault will be created.")
            password = helpers.get_password_for_vault(ctx, new_vault=True)
            vault = Vault()
            vault.add_entry(name=name, issuer=issuer, secret=secret, **parameters)
            try:
                vault.save(path, password)
            except VaultValidationError as e:
                helpers.print_error(str(e))
                raise typer.Exit(ExitCode.VALIDATION_ERROR) from None
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


def generate_code(
    name: str,
    ctx: typer.Context,
    copy: bool = False,
    copy_only: bool = False,
    json_mode: bool = False,
    raw: bool = False,
    quiet: bool = False,
) -> None:
    """Generate and print the TOTP code for the given entry.

    Args:
        name: The name of the entry to generate code for.
        ctx: Typer context with password options.
        copy: Whether to copy the code to clipboard and print.
        copy_only: Whether to copy the code to clipboard without printing.
        json_mode: Output in JSON format.
        raw: Output only the TOTP code.
        quiet: Suppress normal output.
    """

    try:
        helpers.validate_code_options(copy, copy_only, json_mode, raw, quiet)
    except helpers.ValidationError as e:
        helpers.print_error(str(e))
        raise typer.Exit(ExitCode.VALIDATION_ERROR)

    path = _path(ctx)
    # Check vault existence
    vault_exists = None
    try:
        vault_exists = _vault_exists(path)
    except OSError:
        _exit_with_error(
            1, "vault_io_error", "Failed to access vault file.", json_mode, quiet
        )

    if vault_exists is None:
        _exit_with_error(
            1,
            "permission_denied",
            "Cannot access vault directory (permission denied).",
            json_mode,
            quiet,
        )

    if not vault_exists:
        if json_mode:
            print(json.dumps({"error": "vault_missing", "message": "No vault found."}))
        elif not quiet:
            helpers.print_warning("No vault found.")
            helpers.print_info("Nothing to generate.")
        sys.exit(4)

    # Get password
    password = helpers.get_password_for_vault(ctx, new_vault=False)

    try:
        vault = Vault.load(path, password)
        entry = vault.get_entry(name)
        from desktop_2fa.totp.generator import generate

        timestamp = int(time.time())
        code = generate(
            secret=entry.secret,
            timestamp=timestamp,
            digits=entry.digits,
            period=entry.period,
            algorithm=entry.algorithm,
        )
        remaining = entry.period - (timestamp % entry.period)

        # Handle clipboard operations
        clipboard_success = _handle_clipboard(code, copy, copy_only, json_mode, quiet)

        # Output based on mode
        if json_mode:
            output = {
                "account": entry.account_name,
                "issuer": entry.issuer,
                "code": code,
                "valid_for": remaining,
            }
            print(json.dumps(output))
        elif raw:
            print(code)
        elif quiet:
            # No output for quiet mode on success
            pass
        else:
            # Default behavior
            if copy_only and clipboard_success:
                print(f"Code copied to clipboard (valid {remaining}s)")
            elif copy and clipboard_success:
                print(f"Copied to clipboard: {code} (valid {remaining}s)")
            else:
                print(f"{code} (valid {remaining}s)")

    except InvalidPassword:
        _exit_with_error(
            2, "invalid_password", "Invalid vault password.", json_mode, quiet
        )
    except AmbiguousEntry as e:
        _exit_with_error(
            ExitCode.VALIDATION_ERROR, "entry_ambiguous", str(e), json_mode, quiet
        )
    except InvalidSecret:
        _exit_with_error(
            ExitCode.VALIDATION_ERROR,
            "invalid_secret",
            "Invalid TOTP secret. Add a valid replacement from the provider "
            "before removing the legacy entry.",
            json_mode,
            quiet,
        )
    except ValueError as e:
        if "not found" in str(e):
            _exit_with_error(
                3, "entry_not_found", f"Entry '{name}' not found.", json_mode, quiet
            )
        else:
            _exit_with_error(
                2, "invalid_password", "Invalid vault password.", json_mode, quiet
            )
    except CorruptedVault:
        _exit_with_error(
            1, "corrupted_vault", "Vault file is corrupted.", json_mode, quiet
        )
    except UnsupportedFormat:
        _exit_with_error(
            1,
            "unsupported_format",
            "Vault file format is unsupported.",
            json_mode,
            quiet,
        )
    except PermissionDenied:
        _exit_with_error(
            1,
            "permission_denied",
            "Cannot access vault directory (permission denied).",
            json_mode,
            quiet,
        )
    except VaultIOError:
        _exit_with_error(
            1, "vault_io_error", "Failed to access vault file.", json_mode, quiet
        )


def remove_entry(name: str, ctx: typer.Context) -> None:
    """Remove an entry from the vault.

    Args:
        name: The name of the entry to remove.
        ctx: Typer context with password options.
    """
    path = _path(ctx)
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
    except VaultValidationError as e:
        helpers.print_error(str(e))
        raise typer.Exit(ExitCode.VALIDATION_ERROR) from None
    except AmbiguousEntry as e:
        helpers.print_error(str(e))
        raise typer.Exit(ExitCode.VALIDATION_ERROR) from e
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


def rename_entry(
    old: str, new: str, ctx: typer.Context, *, index: int | None = None
) -> None:
    """Rename an entry in the vault.

    Args:
        old: The current name of the entry.
        new: The new name for the entry.
        ctx: Typer context with password options.
        index: Optional one-based index shown by list --indices.
    """
    path = _path(ctx)
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
        vault.rename_entry(old, new, index=index)
        vault.save(path, password)
        helpers.print_success(f"Renamed '{old}' → '{new}'")
    except VaultValidationError as e:
        helpers.print_error(str(e))
        raise typer.Exit(ExitCode.VALIDATION_ERROR) from None
    except (AmbiguousEntry, EntryRenameError) as e:
        helpers.print_error(str(e))
        helpers.print_info(
            "Use 'd2fa list --indices' and 'd2fa rename OLD NEW --index N'."
        )
        raise typer.Exit(ExitCode.VALIDATION_ERROR) from None
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
    path = _path(ctx)
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
    except VaultValidationError as e:
        helpers.print_error(str(e))
        raise typer.Exit(ExitCode.VALIDATION_ERROR) from None
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
    path = _path(ctx)
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
    except VaultValidationError as e:
        helpers.print_error(str(e))
        raise typer.Exit(ExitCode.VALIDATION_ERROR) from None
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
    path = _path(ctx)
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
    except VaultValidationError as e:
        helpers.print_error(str(e))
        raise typer.Exit(ExitCode.VALIDATION_ERROR) from None
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
    path = _path(ctx)
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
    except VaultValidationError as e:
        helpers.print_error(str(e))
        raise typer.Exit(ExitCode.VALIDATION_ERROR) from None
    except PermissionDenied:
        helpers.print_error("Error: Cannot access vault directory (permission denied).")
    except VaultIOError:
        helpers.print_error("Failed to create vault file.")


def unlock_vault(ctx: typer.Context) -> None:
    """Unlock an existing vault and check for weak password.

    Loads and opens an existing vault, verifying the password is correct.
    If configured, prints a non-blocking warning if the vault password
    has a zxcvbn score < 3.

    Args:
        ctx: Typer context with password options.
    """
    path = _path(ctx)

    # Ensure vault exists
    if not helpers.ensure_existing_vault(path):
        return

    # Get password
    password = helpers.get_password_for_vault(ctx, new_vault=False)

    # Load vault and handle errors
    vault = helpers.load_vault_or_print_error(path, password)
    if vault is None:
        return

    helpers.print_success("Vault unlocked successfully.")

    # Check for weak password and warn if configured
    config = helpers.load_config()
    security = config.get("security", {})
    warn_on_weak = security.get("warn_on_weak_existing_passwords", False)

    if warn_on_weak:
        result = evaluate_password_strength(password)
        score = result["score"]
        if score < 3:
            helpers.print_warning(
                f"Warning: Your vault password is weak (score {score}). "
                "Consider changing it."
            )


def change_password(ctx: typer.Context) -> None:
    """Change the vault password.

    Prompts for the current password, verifies the vault can be opened,
    then prompts for a new password (with confirmation), enforces strength
    checks, and re-encrypts the vault with the new password.

    Args:
        ctx: Typer context with password options.
    """
    path = _path(ctx)

    # Ensure vault exists
    if not helpers.ensure_existing_vault(path):
        return

    # Get current password and open vault
    current_password = helpers.get_password_for_vault(ctx, new_vault=False)
    vault = helpers.load_vault_or_print_error(path, current_password)
    if vault is None:
        return

    # Prompt for new password (with confirmation)
    new_password = helpers.prompt_new_password(ctx)
    if new_password is None:
        return

    # Enforce password strength
    if not helpers._should_skip_password_checks(ctx):
        helpers._enforce_password_strength(new_password)

    # Re-encrypt vault with new password
    try:
        vault.save(path, new_password)
        helpers.print_success("Vault password changed successfully.")
    except VaultValidationError as e:
        helpers.print_error(str(e))
        raise typer.Exit(ExitCode.VALIDATION_ERROR) from None
    except PermissionDenied:
        helpers.print_error("Error: Cannot access vault directory (permission denied).")
    except VaultIOError:
        helpers.print_error("Failed to save vault file.")
