"""CLI command implementations for Desktop 2FA."""

from __future__ import annotations

import os
import time
from pathlib import Path

import typer

import desktop_2fa.cli.helpers as helpers
from desktop_2fa.constants import ExitCode
from desktop_2fa.utils.base32 import InvalidSecret, normalize_base32
from desktop_2fa.vault import Vault
from desktop_2fa.vault.password_strength import evaluate_password_strength
from desktop_2fa.vault.vault import (
    PermissionDenied,
    VaultNotFound,
)

from .errors import CLI_ERRORS, command_errors, exit_for_error, report_error
from .output import DUPLICATE_WARNING, code_result, fail, failure


def _handle_clipboard(code: str, copy: bool, copy_only: bool) -> bool:
    """Handle clipboard operations and return success status.

    Args:
        code: The TOTP code to copy.
        copy: Whether to copy and print.
        copy_only: Whether to copy without printing.

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
            message = "Clipboard not available on this system."
            if copy_only:
                raise SystemExit(
                    failure(
                        ExitCode.CLIPBOARD_UNAVAILABLE, "clipboard_unavailable", message
                    )
                ) from None
            helpers.print_warning(message)
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
        helpers.print_error(
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


@command_errors
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
    except CLI_ERRORS as error:
        exit_for_error(error)

    # DEF-02: Handle permission denied during existence check
    if vault_exists is None:
        exit_for_error(PermissionDenied())

    if not vault_exists:
        helpers.print_warning("No vault found.")
        helpers.print_info("A new encrypted vault will be created.")
        password = helpers.get_password_for_vault(ctx, new_vault=True)
        vault = Vault()
        vault.add_entry(name=name, issuer=issuer, secret=secret, **parameters)
        try:
            vault.save(path, password)
        except CLI_ERRORS as error:
            exit_for_error(error)
        print(f"Vault created at {path}")
        print(f"Entry added: {name}")
    else:
        password = helpers.get_password_for_vault(ctx, new_vault=False)
        try:
            vault = Vault.load(path, password)
            if vault.duplicate_account_names:
                helpers.print_warning(DUPLICATE_WARNING)
            vault.add_entry(name=name, issuer=issuer, secret=secret, **parameters)
            vault.save(path, password)
            helpers.print_success(f"Entry added: {name}")
        except CLI_ERRORS as error:
            exit_for_error(error)


@command_errors
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
    except CLI_ERRORS as error:
        exit_for_error(error)

    # DEF-02: Handle permission denied during existence check
    if vault_exists is None:
        exit_for_error(PermissionDenied())

    if not vault_exists:
        helpers.print_warning("No vault found.")
        helpers.print_info("A new encrypted vault will be created.")
        password = helpers.get_password_for_vault(ctx, new_vault=True)
        vault = Vault()
        try:
            vault.save(path, password)
        except CLI_ERRORS as error:
            exit_for_error(error)
        print(f"Vault created at {path}")
        print("No entries found.")
    else:
        password = helpers.get_password_for_vault(ctx, new_vault=False)
        try:
            vault = Vault.load(path, password)
            if vault.duplicate_account_names:
                helpers.print_warning(DUPLICATE_WARNING)
        except CLI_ERRORS as error:
            exit_for_error(error)
        if vault.entries:
            helpers.print_entries_table(vault.entries, show_indices=show_indices)
        else:
            if interactive:
                helpers.print_info("No entries found.")


@command_errors
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
    except CLI_ERRORS as error:
        exit_for_error(error)

    # DEF-02: Handle permission denied during existence check
    if vault_exists is None:
        exit_for_error(PermissionDenied())

    if not vault_exists:
        helpers.print_warning("No vault found.")
        helpers.print_info("A new encrypted vault will be created.")
        password = helpers.get_password_for_vault(ctx, new_vault=True)
        vault = Vault()
        vault.add_entry(name=name, issuer=issuer, secret=secret, **parameters)
        try:
            vault.save(path, password)
        except CLI_ERRORS as error:
            exit_for_error(error)
        print(f"Vault created at {path}")
        print(f"Entry added: {name}")
    else:
        password = helpers.get_password_for_vault(ctx, new_vault=False)
        try:
            vault = Vault.load(path, password)
            if vault.duplicate_account_names:
                helpers.print_warning(DUPLICATE_WARNING)
            vault.add_entry(name=name, issuer=issuer, secret=secret, **parameters)
            vault.save(path, password)
            helpers.print_success(f"Entry added: {name}")
        except CLI_ERRORS as error:
            exit_for_error(error)


@command_errors
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
        fail(ExitCode.VALIDATION_ERROR, "invalid_options", str(e))

    path = _path(ctx)
    # Check vault existence
    vault_exists = None
    try:
        vault_exists = _vault_exists(path)
    except CLI_ERRORS as error:
        raise SystemExit(
            report_error(error, json_mode=json_mode, quiet=quiet)
        ) from None

    if vault_exists is None:
        raise SystemExit(
            report_error(PermissionDenied(), json_mode=json_mode, quiet=quiet)
        )

    if not vault_exists:
        raise SystemExit(
            report_error(VaultNotFound(), json_mode=json_mode, quiet=quiet)
        )

    password = helpers.get_password_for_vault(ctx, new_vault=False)

    try:
        vault = Vault.load(path, password)
        if vault.duplicate_account_names:
            helpers.print_warning(DUPLICATE_WARNING)
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
        clipboard_success = _handle_clipboard(code, copy, copy_only)

        code_result(
            entry,
            code,
            remaining,
            copy=copy,
            copy_only=copy_only,
            clipboard_success=clipboard_success,
        )

    except CLI_ERRORS as error:
        raise SystemExit(
            report_error(error, json_mode=json_mode, quiet=quiet)
        ) from None


@command_errors
def remove_entry(name: str, ctx: typer.Context) -> None:
    """Remove an entry from the vault.

    Args:
        name: The name of the entry to remove.
        ctx: Typer context with password options.
    """
    path = _path(ctx)
    try:
        vault_exists = _vault_exists(path)
    except CLI_ERRORS as error:
        exit_for_error(error)

    # DEF-02: Handle permission denied during existence check
    if vault_exists is None:
        exit_for_error(PermissionDenied())

    if not vault_exists:
        helpers.print_warning("No vault found.")
        raise typer.Exit(ExitCode.VAULT_MISSING)
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
        vault = Vault.load(path, password)
        if vault.duplicate_account_names:
            helpers.print_warning(DUPLICATE_WARNING)
        vault.remove_entry(name)
        vault.save(path, password)
        helpers.print_success(f"Removed entry: {name}")
    except CLI_ERRORS as error:
        exit_for_error(error)


@command_errors
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
    except CLI_ERRORS as error:
        exit_for_error(error)

    # DEF-02: Handle permission denied during existence check
    if vault_exists is None:
        exit_for_error(PermissionDenied())

    if not vault_exists:
        helpers.print_warning("No vault found.")
        raise typer.Exit(ExitCode.VAULT_MISSING)
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
        vault = Vault.load(path, password)
        if vault.duplicate_account_names:
            helpers.print_warning(DUPLICATE_WARNING)
        vault.rename_entry(old, new, index=index)
        vault.save(path, password)
        helpers.print_success(f"Renamed '{old}' → '{new}'")
    except CLI_ERRORS as error:
        exit_for_error(error)


@command_errors
def export_vault(export_path: str, ctx: typer.Context) -> None:
    """Export the vault to a new file.

    Args:
        export_path: Path where the vault will be exported.
        ctx: Typer context with password options.
    """
    path = _path(ctx)
    try:
        vault_exists = _vault_exists(path)
    except CLI_ERRORS as error:
        exit_for_error(error)

    # DEF-02: Handle permission denied during existence check
    if vault_exists is None:
        exit_for_error(PermissionDenied())

    if not vault_exists:
        helpers.print_warning("No vault found.")
        raise typer.Exit(ExitCode.VAULT_MISSING)
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
        vault = Vault.load(path, password)
        if vault.duplicate_account_names:
            helpers.print_warning(DUPLICATE_WARNING)
        vault.save(Path(export_path), password)
        helpers.print_success(f"Exported vault to: {export_path}")
    except CLI_ERRORS as error:
        exit_for_error(error)


@command_errors
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
    except CLI_ERRORS as error:
        exit_for_error(error)

    # DEF-02: Handle permission denied during existence check
    if vault_exists is None:
        exit_for_error(PermissionDenied())

    if vault_exists and not force:
        helpers.print_error(
            "Refusing to overwrite existing vault. Use --force to proceed."
        )
        raise typer.Exit(ExitCode.VALIDATION_ERROR)
    if vault_exists and force:
        helpers.print_error("Existing vault will be overwritten.")
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
        vault = Vault.load(Path(source), password)
        vault.save(path, password)
        helpers.print_success(f"Vault imported from {source}")
    except CLI_ERRORS as error:
        exit_for_error(error)


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


@command_errors
def backup_vault(ctx: typer.Context) -> None:
    """Create a backup of the vault.

    Args:
        ctx: Typer context with password options.
    """
    path = _path(ctx)
    try:
        vault_exists = _vault_exists(path)
    except CLI_ERRORS as error:
        exit_for_error(error)

    # DEF-02: Handle permission denied during existence check
    if vault_exists is None:
        exit_for_error(PermissionDenied())

    if not vault_exists:
        helpers.print_warning("No vault found.")
        raise typer.Exit(ExitCode.VAULT_MISSING)
    password = helpers.get_password_for_vault(ctx, new_vault=False)
    try:
        vault = Vault.load(path, password)
        if vault.duplicate_account_names:
            helpers.print_warning(DUPLICATE_WARNING)
        backup_path = _get_backup_path(path)
        vault.save(backup_path, password)
        helpers.print_success(f"Backup created: {backup_path}")
    except CLI_ERRORS as error:
        exit_for_error(error)


@command_errors
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
    except CLI_ERRORS as error:
        exit_for_error(error)

    # DEF-02: Handle permission denied during existence check
    if vault_exists is None:
        exit_for_error(PermissionDenied())

    if vault_exists and not force:
        helpers.print_info("Vault already exists.")
        helpers.print_info("Use --force to overwrite.")
        raise typer.Exit(ExitCode.VALIDATION_ERROR)
    if vault_exists and force:
        helpers.print_error("Existing vault will be overwritten.")

    # DEF-02: Check for permission issues before trying to create vault
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except CLI_ERRORS as error:
        exit_for_error(error)

    password = helpers.get_password_for_vault(ctx, new_vault=True)
    vault = Vault()
    try:
        vault.save(path, password)
        print(f"Vault created at {path}")
    except CLI_ERRORS as error:
        exit_for_error(error)


@command_errors
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
        raise typer.Exit(ExitCode.VAULT_MISSING)

    # Get password
    password = helpers.get_password_for_vault(ctx, new_vault=False)

    # Load vault and handle errors
    vault = helpers.load_vault_or_print_error(path, password)
    if vault is None:
        raise typer.Exit(ExitCode.GENERAL_ERROR)

    # Check for weak password and warn if configured
    config = helpers.load_config()
    security = config.get("security", {})
    warn_on_weak = security.get("warn_on_weak_existing_passwords", False)

    warning = None
    if warn_on_weak:
        result = evaluate_password_strength(password)
        score = result["score"]
        if score < 3:
            warning = (
                f"Warning: Your vault password is weak (score {score}). "
                "Consider changing it."
            )

    helpers.print_success("Vault unlocked successfully.")
    if warning:
        helpers.print_warning(warning)


@command_errors
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
        raise typer.Exit(ExitCode.VAULT_MISSING)

    # Get current password and open vault
    current_password = helpers.get_password_for_vault(ctx, new_vault=False)
    vault = helpers.load_vault_or_print_error(path, current_password)
    if vault is None:
        raise typer.Exit(ExitCode.GENERAL_ERROR)

    # Prompt for new password (with confirmation)
    new_password = helpers.prompt_new_password(ctx)
    if new_password is None:
        raise typer.Exit(ExitCode.VALIDATION_ERROR)

    # Enforce password strength
    if not helpers._should_skip_password_checks(ctx):
        helpers._enforce_password_strength(new_password)

    # Re-encrypt vault with new password
    try:
        vault.save(path, new_password)
        helpers.print_success("Vault password changed successfully.")
    except CLI_ERRORS as error:
        exit_for_error(error)
