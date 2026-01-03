"""CLI helper functions for Desktop 2FA."""

import base64
import time
import urllib.parse
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console

from desktop_2fa.vault import Vault

if TYPE_CHECKING:
    from desktop_2fa.vault.models import TotpEntry

console = Console()


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
    return Vault.load(path, password)


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
    if new_vault:
        pwd = typer.prompt("[cyan]Enter new vault password:[/cyan]", hide_input=True)
        confirm = typer.prompt("[cyan]Confirm vault password:[/cyan]", hide_input=True)
        if pwd != confirm:
            print_error("Passwords do not match. Please try again.")
            raise typer.Exit(1)
    else:
        pwd = typer.prompt("[cyan]Enter vault password:[/cyan]", hide_input=True)
    return pwd  # type: ignore[no-any-return]


def get_password_from_cli(ctx: typer.Context) -> str:
    """Legacy alias for backward compatibility."""
    return get_password_for_vault(ctx, new_vault=False)


def timestamp() -> str:
    return str(int(time.time()))


# Rich-based output helpers
def print_success(message: str) -> None:
    """Print a success message in green."""
    console.print(f"[green]{message}[/green]")


def print_warning(message: str) -> None:
    """Print a warning message in yellow."""
    console.print(f"[yellow]{message}[/yellow]")


def print_error(message: str) -> None:
    """Print an error message in red."""
    console.print(f"[red]{message}[/red]")


def print_info(message: str) -> None:
    """Print an info message in blue."""
    console.print(f"[blue]{message}[/blue]")


def print_prompt(message: str) -> None:
    """Print a prompt message in cyan."""
    console.print(f"[cyan]{message}[/cyan]")


def print_header(message: str) -> None:
    """Print a header message in bold white."""
    console.print(f"[bold white]{message}[/bold white]")


def print_entries_table(entries: list["TotpEntry"]) -> None:
    """Print entries in a formatted table."""
    if not entries:
        print_info("No entries found.")
        return

    # For now, print simple format to keep tests passing
    for entry in entries:
        print(f"- {entry.account_name} ({entry.issuer})")


def validate_base32(secret: str) -> bool:
    """Validate if a string is valid Base32."""
    try:
        # Remove padding and spaces, convert to uppercase
        cleaned = secret.replace(" ", "").replace("=", "").upper()
        # Check if all characters are valid Base32
        if not all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in cleaned):
            return False
        # Try to decode to verify it's valid
        base64.b32decode(cleaned + "=" * ((8 - len(cleaned) % 8) % 8))
        return True
    except Exception:
        return False


def parse_otpauth_url(url: str) -> dict[str, str]:
    """Parse an otpauth:// URL and extract issuer, label, and secret."""
    if not url.startswith("otpauth://"):
        raise ValueError("Invalid otpauth URL")

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "otpauth" or parsed.netloc != "totp":
        raise ValueError("Only TOTP otpauth URLs are supported")

    # Parse the path: /Issuer:Label or /Issuer or /:Label
    path = parsed.path.lstrip("/")
    if ":" in path:
        issuer, label = path.split(":", 1)
    else:
        issuer = path
        label = path

    # Parse query parameters
    query = urllib.parse.parse_qs(parsed.query)
    secret = query.get("secret", [None])[0]
    if not secret:
        raise ValueError("Secret parameter is required")

    url_issuer = query.get("issuer", [None])[0]
    if url_issuer and not issuer:
        issuer = url_issuer

    return {
        "issuer": issuer or "Unknown",
        "label": label or issuer or "Unknown",
        "secret": secret,
    }
