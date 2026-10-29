"""CLI helper functions for Desktop 2FA."""

import getpass
import math
import os
import re
import tomllib
import urllib.parse
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypedDict, cast

import typer
from rich import print as rprint
from rich.text import Text

from desktop_2fa.constants import ExitCode
from desktop_2fa.utils.base32 import InvalidSecret, decode_base32, normalize_base32
from desktop_2fa.vault import Vault
from desktop_2fa.vault.password_strength import evaluate_password_strength

from .errors import CLI_ERRORS, exit_for_error
from .output import diagnostic, fail, output_mode


class ValidationError(Exception):
    """Raised when CLI option validation fails."""


if TYPE_CHECKING:
    from desktop_2fa.vault.models import TotpEntry


class TotpParameters(TypedDict):
    algorithm: Literal["SHA1", "SHA256", "SHA512"]
    digits: Literal[6, 7, 8]
    period: int


class ParsedOtpauth(TotpParameters):
    issuer: str
    label: str
    secret: str


def list_entries(path: Path, password: str) -> None:
    """List all entries in the vault.

    Args:
        path: Path to the vault file.
        password: Password to decrypt the vault.
    """
    vault = Vault.load(path, password)
    for entry in vault.entries:
        print(f"- {entry.account_name} ({entry.issuer})")


def add_entry(
    path: Path, issuer: str, account: str, secret: str, password: str
) -> None:
    """Add a new entry to the vault.

    Args:
        path: Path to the vault file.
        issuer: The issuer name.
        account: The account name.
        secret: The Base32-encoded TOTP secret.
        password: Password to encrypt the vault.
    """
    secret = normalize_base32(secret)
    vault = Vault.load(path, password)
    vault.add_entry(name=account, issuer=issuer, secret=secret)
    vault.save(path, password)
    print(f"Added entry: {account}")


def generate_code(path: Path, name: str, password: str) -> None:
    """Generate and print the TOTP code for the given entry.

    Args:
        path: Path to the vault file.
        name: The name of the entry.
        password: Password to decrypt the vault.
    """
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
    """Remove an entry from the vault.

    Args:
        path: Path to the vault file.
        name: The name of the entry to remove.
        password: Password to decrypt the vault.
    """
    vault = Vault.load(path, password)
    vault.remove_entry(name)
    vault.save(path, password)
    print(f"Removed entry: {name}")


def rename_entry(
    path: Path, old: str, new: str, password: str, *, index: int | None = None
) -> None:
    """Rename an entry in the vault.

    Args:
        path: Path to the vault file.
        old: The current name of the entry.
        new: The new name for the entry.
        password: Password to decrypt the vault.
        index: Optional one-based index shown by list --indices.
    """
    vault = Vault.load(path, password)
    vault.rename_entry(old, new, index=index)

    vault.save(path, password)
    print(f"Renamed '{old}' → '{new}'")


def export_vault(path: Path, export_path: Path, password: str) -> None:
    """Export the vault to a new file.

    Args:
        path: Path to the source vault file.
        export_path: Path where the vault will be exported.
        password: Password to decrypt the vault.
    """
    vault = Vault.load(path, password)
    vault.save(export_path, password)
    print(f"Exported vault to: {export_path}")


def import_vault(path: Path, import_path: Path, password: str) -> None:
    """Import a vault from a source file.

    Args:
        path: Path to the destination vault file.
        import_path: Path to the source vault file.
        password: Password to encrypt the destination vault.
    """
    vault = Vault.load(import_path, password=password)
    vault.save(path, password)
    print("Vault imported from")


def backup_vault(path: Path, backup_path: Path, password: str) -> None:
    """Create a backup of the vault file.

    Args:
        path: Path to the source vault file.
        backup_path: Path where the backup will be created.
        password: Password to decrypt the vault.
    """
    vault = Vault.load(path, password)
    vault.save(backup_path, password)
    print("Backup created:")


def resolve_vault_path(vault_path: str | Path | None = None) -> str:
    """Resolve the vault path from an explicit value, environment, or default.

    Returns:
        Path to the vault file as a string.
    """
    if not vault_path:
        vault_path = os.getenv("DESKTOP_2FA_VAULT")

    if vault_path:
        path = Path(vault_path)
        try:
            return str(path.expanduser())
        except RuntimeError:
            return str(path)

    return str(Path.home() / ".desktop-2fa" / "vault")


def get_vault_path() -> str:
    """Get the resolved path for the vault file."""
    return resolve_vault_path()


def load_vault(path: Path, password: str) -> Vault:
    """Load the vault from the specified path.

    Args:
        path: Path to the vault file.
        password: Password to decrypt the vault.

    Returns:
        The loaded Vault instance.
    """
    return Vault.load(path, password)


def save_vault(path: Path, vault: Vault, password: str) -> None:
    """Save the vault to the specified path.

    Args:
        path: Path to save the vault file.
        vault: The Vault instance to save.
        password: Password to encrypt the vault.
    """
    vault.save(path, password)


def get_password_for_vault(ctx: typer.Context, new_vault: bool = False) -> str:
    """Get the password for vault operations.

    Args:
        ctx: Typer context with password options.
        new_vault: Whether creating a new vault (affects prompts).

    Returns:
        The password string.

    Raises:
        typer.Exit: If password cannot be obtained or is empty.
    """
    password = ctx.obj.get("password")
    password_file = ctx.obj.get("password_file")
    interactive = ctx.obj.get("interactive")

    # Both flags provided
    if password and password_file:
        fail(
            ExitCode.VALIDATION_ERROR,
            "password_error",
            "Cannot specify both --password and --password-file",
        )

    # DEF-01: Immediately reject empty passwords (direct --password "")
    if password == "":
        fail(ExitCode.VALIDATION_ERROR, "password_error", "Password cannot be empty.")

    # Direct password
    if password:
        return password  # type: ignore[no-any-return]

    # Password from file
    if password_file:
        try:
            with open(password_file, "r") as f:
                pwd = f.read().strip()
                # DEF-01: Immediately reject empty passwords
                if not pwd:
                    fail(
                        ExitCode.VALIDATION_ERROR,
                        "password_error",
                        "Password cannot be empty.",
                    )
                return pwd
        except FileNotFoundError:
            fail(ExitCode.GENERAL_ERROR, "password_error", "Password file not found.")
        except OSError:
            fail(
                ExitCode.GENERAL_ERROR, "password_error", "Error reading password file."
            )

    # Quiet must not invoke getpass: its fallback can print its own warnings.
    if output_mode.get().quiet:
        fail(
            ExitCode.VALIDATION_ERROR,
            "password_error",
            "Password not provided; quiet mode requires --password or --password-file.",
        )

    # No password provided
    if not interactive:
        fail(
            ExitCode.VALIDATION_ERROR,
            "password_error",
            "Password not provided and not running in interactive mode",
        )

    # Interactive mode → prompt
    if new_vault:
        print_prompt("Enter new vault password:")
        pwd = getpass.getpass("")
        # DEF-01: Immediately reject empty passwords
        if not pwd:
            fail(
                ExitCode.VALIDATION_ERROR, "password_error", "Password cannot be empty."
            )
        print_prompt("Confirm vault password:")
        confirm = getpass.getpass("")
        # DEF-01: Immediately reject empty passwords
        if not confirm:
            fail(
                ExitCode.VALIDATION_ERROR, "password_error", "Password cannot be empty."
            )
        if pwd != confirm:
            fail(
                ExitCode.VALIDATION_ERROR,
                "password_error",
                "Passwords do not match. Please try again.",
            )
        # Check password strength
        if not _should_skip_password_checks(ctx):
            _enforce_password_strength(pwd)
    else:
        print_prompt("Enter vault password:")
        pwd = getpass.getpass("")
        # DEF-01: Immediately reject empty passwords
        if not pwd:
            fail(
                ExitCode.VALIDATION_ERROR, "password_error", "Password cannot be empty."
            )
    return pwd


def create_vault(path: Path, password: str) -> None:
    """Create a new vault at the specified path.

    Args:
        path: Path where the vault will be created.
        password: Password to encrypt the vault.
    """
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(path, password)
    print(f"Vault created at {path}")


def _read_password_file(password_file: str) -> str:
    """Read password from a file.

    Args:
        password_file: Path to the file containing the password.

    Returns:
        The password read from the file.

    Raises:
        typer.Exit: If the file cannot be read.
    """
    try:
        with open(password_file, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        print("Error: Password file not found.")
        raise typer.Exit(ExitCode.GENERAL_ERROR)
    except OSError:
        print("Error reading password file.")
        raise typer.Exit(ExitCode.GENERAL_ERROR)


def load_config() -> dict[str, Any]:
    """Load configuration from ~/.config/d2fa/config.toml.

    Returns:
        Dictionary containing the configuration.
    """
    config_path = Path.home() / ".config" / "d2fa" / "config.toml"
    if not config_path.exists():
        return {}
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def calculate_entropy(password: str) -> float:
    """Calculate the entropy of a password.

    Args:
        password: The password to analyze.

    Returns:
        The estimated entropy in bits.
    """
    words = password.split()
    if len(words) >= 4:
        return 11 * len(words)
    # Determine character set size
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    N = 0
    if has_lower:
        N += 26
    if has_upper:
        N += 26
    if has_digit:
        N += 10
    if has_symbol:
        N += 32  # approximate
    if N == 0:
        N = 1
    return len(password) * math.log2(N)


def _should_skip_password_checks(ctx: typer.Context) -> bool:
    """Check if password strength checks should be skipped.

    Args:
        ctx: Typer context with options.

    Returns:
        True if checks should be skipped, False otherwise.
    """
    return (
        ctx.obj.get("allow_weak_passwords", False)
        or os.getenv("D2FA_ALLOW_WEAK_PASSWORDS") == "1"
        or os.getenv("PYTEST_CURRENT_TEST") is not None
    )


def _get_password_strength_threshold(config: dict[str, Any]) -> int:
    """Get the password strength threshold from config.

    Implements Option A: Configuration Mapping
    - If min_password_entropy is set, treat it as requiring zxcvbn score >= 3
    - Otherwise use default threshold of 3

    Args:
        config: Configuration dictionary loaded from ~/.config/d2fa/config.toml

    Returns:
        The zxcvbn score threshold (3 for strong passwords)
    """
    security = config.get("security", {})
    # Check if legacy min_password_entropy is configured
    if "min_password_entropy" in security:
        # Legacy config present: map to zxcvbn score >= 3 requirement
        return 3
    # Default threshold
    return 3


def _enforce_password_strength(password: str) -> None:
    """Enforce password strength requirements using zxcvbn.

    Uses zxcvbn score < 3 as the threshold for weak passwords.
    Respects legacy min_password_entropy config (mapped to threshold 3).

    Args:
        password: The password to validate.

    Raises:
        typer.Exit: If password is too weak and rejection is enabled.
    """
    # Guard against empty passwords which crash zxcvbn
    if not password or not password.strip():
        print_error("Password cannot be empty")
        raise typer.Exit(ExitCode.VALIDATION_ERROR)

    config = load_config()
    security = config.get("security", {})
    reject_weak = security.get("reject_weak_passwords", False)
    threshold = _get_password_strength_threshold(config)

    result = evaluate_password_strength(password)
    score = result["score"]
    feedback = result["feedback"]
    if score < threshold:
        warning = feedback.get("warning") or ""
        suggestions = " ".join(feedback.get("suggestions", []))
        message = f"Password too weak (score {score} < {threshold}). {warning} {suggestions}".strip()
        if reject_weak:
            print_error(message)
            raise typer.Exit(ExitCode.VALIDATION_ERROR)
        else:
            print_warning(message)
            if not typer.confirm("Continue with weak password?"):
                raise typer.Exit(ExitCode.VALIDATION_ERROR)


def get_password_from_cli(ctx: typer.Context) -> str:
    """Get the password for vault operations from CLI context.

    Args:
        ctx: Typer context with password options.

    Returns:
        The password string.

    Raises:
        typer.Exit: If password cannot be obtained.
    """
    return get_password_for_vault(ctx, new_vault=False)


# Rich-based output helpers
def print_success(message: str) -> None:
    """Print a success message in green."""
    rprint(Text(message, style="green"))


def print_warning(message: str) -> None:
    """Print a literal warning on stderr unless quiet."""
    diagnostic(message)


def print_error(message: str) -> None:
    """Print a literal error on stderr unless quiet."""
    diagnostic(message)


def print_info(message: str) -> None:
    """Print an info message in white."""
    rprint(Text(message, style="white"))


def print_prompt(message: str) -> None:
    """Print a prompt on stderr unless quiet."""
    if not output_mode.get().quiet:
        typer.echo(message, err=True)


def print_header(message: str) -> None:
    """Print a header message in bold white."""
    rprint(Text(message, style="bold white"))


def print_entries_table(
    entries: list["TotpEntry"], *, show_indices: bool = False
) -> None:
    """Print entries in a formatted table."""
    if not entries:
        print_info("No entries found.")
        return

    for index, entry in enumerate(entries, start=1):
        if show_indices:
            # Escape line breaks so one numbered record stays on one line.
            print(f"[{index}] {entry.account_name!r} ({entry.issuer!r})")
        else:
            print(f"- {entry.account_name} ({entry.issuer})")


def validate_base32(secret: str) -> bool:
    """Validate if a string is valid Base32."""
    try:
        decode_base32(secret)
        return True
    except InvalidSecret:
        return False


def parse_otpauth_url(url: str) -> ParsedOtpauth:
    """Validate TOTP provisioning data without dropping code parameters."""
    if not url.startswith("otpauth://"):
        raise ValueError("Invalid otpauth URL")

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "otpauth" or parsed.netloc != "totp":
        raise ValueError("Only TOTP otpauth URLs are supported")

    if parsed.fragment or re.search(r"%(?![0-9a-fA-F]{2})", url):
        raise ValueError("Invalid otpauth URL encoding or fragment")
    path = urllib.parse.unquote(parsed.path.removeprefix("/"), errors="strict")
    if ":" in path:
        prefix, label = path.split(":", 1)
        label = label.lstrip(" ")
        if ":" in label:
            raise ValueError("Issuer and account label cannot contain colons")
    else:
        prefix = ""
        label = path
    if not label:
        raise ValueError("Account label is required")

    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True, errors="strict")
    for parameter in ("secret", "issuer", "algorithm", "digits", "period", "counter"):
        if len(query.get(parameter, [])) > 1:
            raise ValueError(f"Duplicate {parameter} parameter")
    if "counter" in query:
        raise ValueError("Counter is not supported for TOTP provisioning")
    secret = query.get("secret", [""])[0]
    if not secret:
        raise ValueError("Secret parameter is required")

    url_issuer = query.get("issuer", [""])[0]
    if "issuer" in query and not url_issuer:
        raise ValueError("Issuer parameter cannot be empty")
    if ":" in url_issuer:
        raise ValueError("Issuer cannot contain colons")
    if prefix and url_issuer and prefix != url_issuer:
        raise ValueError("Issuer parameter conflicts with the label prefix")
    issuer = url_issuer or prefix or (label if ":" not in path else "Unknown")

    algorithm = query.get("algorithm", ["SHA1"])[0].upper()
    if algorithm not in ("SHA1", "SHA256", "SHA512"):
        raise ValueError("Unsupported algorithm (expected SHA1, SHA256 or SHA512)")
    digits = query.get("digits", ["6"])[0]
    if digits not in ("6", "7", "8"):
        raise ValueError("Invalid digits (expected 6, 7 or 8)")
    period = query.get("period", ["30"])[0]
    if not period.isascii() or not period.isdecimal() or int(period) <= 0:
        raise ValueError("Period must be a positive integer")

    return {
        "issuer": issuer,
        "label": label,
        "secret": normalize_base32(secret),
        "algorithm": cast(Literal["SHA1", "SHA256", "SHA512"], algorithm),
        "digits": cast(Literal[6, 7, 8], int(digits)),
        "period": int(period),
    }


def validate_code_options(
    copy: bool, copy_only: bool, json_mode: bool, raw: bool, quiet: bool
) -> None:
    """Validate mutually exclusive options for code command.

    Args:
        copy: Whether to copy code to clipboard and print.
        copy_only: Whether to copy code to clipboard without printing.
        json_mode: Whether to output in JSON format.
        raw: Whether to output only the TOTP code.
        quiet: Whether to suppress normal output.

    Raises:
        ValidationError: If validation fails.
    """
    if copy and copy_only:
        raise ValidationError("--copy and --copy-only are mutually exclusive")
    if json_mode and (raw or quiet or copy or copy_only):
        raise ValidationError(
            "--json conflicts with --raw, --quiet, --copy, and --copy-only"
        )
    if raw and (json_mode or quiet or copy or copy_only):
        raise ValidationError(
            "--raw conflicts with --json, --quiet, --copy, and --copy-only"
        )
    if quiet and (json_mode or raw):
        raise ValidationError("--quiet conflicts with --json and --raw")


# ============================================================================
# Vault Helper Functions for Code Reuse
# ============================================================================


def ensure_existing_vault(path: Path) -> bool:
    """Check that vault exists at the given path.

    Args:
        path: Path to the vault file.

    Returns:
        True if vault exists. Failures print a message and raise typer.Exit.
    """
    from desktop_2fa.cli.commands import _vault_exists

    try:
        vault_exists = _vault_exists(path)
    except OSError as error:
        exit_for_error(error)

    if vault_exists is None:
        print_error("Error: Cannot access vault directory (permission denied).")
        raise typer.Exit(ExitCode.GENERAL_ERROR)

    if not vault_exists:
        print_warning("No vault found.")
        raise typer.Exit(ExitCode.VAULT_MISSING)

    return True


def load_vault_or_print_error(path: Path, password: str) -> "Vault":
    """Load vault and handle errors with user-friendly messages.

    Args:
        path: Path to the vault file.
        password: Password to decrypt the vault.

    Returns:
        Loaded Vault object. Expected failures print a message and raise typer.Exit.
    """
    try:
        return Vault.load(path, password)
    except CLI_ERRORS as error:
        exit_for_error(error)


def prompt_new_password(ctx: typer.Context) -> str:
    """Prompt for new password with confirmation.

    Args:
        ctx: Typer context.

    Returns:
        Confirmed new password string. Invalid input raises typer.Exit with status 6.
    """
    data = ctx.obj or {}
    interactive = data.get("interactive")
    if not interactive:
        print_error("Password change requires interactive mode.")
        raise typer.Exit(ExitCode.VALIDATION_ERROR)

    rprint(Text("Enter new vault password:", style="cyan"))
    new_password = getpass.getpass("")

    # Immediately reject empty passwords
    if not new_password:
        print_error("Password cannot be empty.")
        raise typer.Exit(ExitCode.VALIDATION_ERROR)

    rprint(Text("Confirm new vault password:", style="cyan"))
    confirm_password = getpass.getpass("")

    # Immediately reject empty passwords
    if not confirm_password:
        print_error("Password cannot be empty.")
        raise typer.Exit(ExitCode.VALIDATION_ERROR)

    if new_password != confirm_password:
        print_error("Passwords do not match. Please try again.")
        raise typer.Exit(ExitCode.VALIDATION_ERROR)

    return new_password
