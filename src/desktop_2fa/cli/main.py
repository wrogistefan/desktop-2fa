"""CLI main entry point for Desktop 2FA."""

import os
import sys

import typer
from rich import print as rprint
from rich.text import Text

from desktop_2fa import __version__

from . import commands, helpers


def is_interactive() -> bool:
    """Check if we're running in interactive mode.

    For tests, this can be overridden with DESKTOP_2FA_FORCE_INTERACTIVE=1
    environment variable. For real usage, it uses TTY detection.
    """
    if os.getenv("DESKTOP_2FA_FORCE_INTERACTIVE") == "1":
        return True
    return sys.stdin.isatty() and sys.stdout.isatty()


app = typer.Typer(help="Desktop‑2FA — secure offline TOTP authenticator")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
    password: str = typer.Option(
        None, "--password", help="Password for vault encryption/decryption"
    ),
    password_file: str = typer.Option(
        None,
        "--password-file",
        help="File containing password for vault encryption/decryption",
    ),
    allow_weak_passwords: bool = typer.Option(
        False, "--allow-weak-passwords", help="Allow weak passwords"
    ),
) -> None:
    """
    Global CLI callback — initializes context and handles --version and no-args case.

    Contract (from tests):
    - `desktop-2fa --version` → prints version, exit 0
    - `desktop-2fa` (no command) → prints version, exit 0
    - any command → ctx.obj must be initialized and no early exit
    """
    # ALWAYS initialize ctx.obj - regardless of command/options
    ctx.obj = {
        "password": password,
        "password_file": password_file,
        "interactive": is_interactive(),
        "allow_weak_passwords": allow_weak_passwords,
    }

    # If user provided --version OR no command was given,
    # behave like "print version and exit".
    # invoke_without_command=True guarantees callback is called even without a command.
    if version or ctx.invoked_subcommand is None:
        print(f"Desktop-2FA v{__version__}")
        raise typer.Exit()


@app.command("list")
def list_cmd(ctx: typer.Context) -> None:
    """List all TOTP entries in the vault."""
    commands.list_entries(ctx)


@app.command("add")
def add_cmd(
    ctx: typer.Context,
    name: str = typer.Argument(None, help="Unique name identifier"),
    issuer: str = typer.Argument(None, help="Issuer name or otpauth:// URL"),
    secret: str = typer.Argument(None, help="TOTP secret (Base32)"),
) -> None:
    """Add a new TOTP entry to the vault.

    Args:
        ctx: Typer context object containing configuration.
        name: Unique name identifier for the entry.
        issuer: Issuer name or otpauth:// URL.
        secret: TOTP secret in Base32 format.
    """
    # Interactive mode: prompt for missing arguments
    interactive = ctx.obj.get("interactive", False)
    if interactive and (name is None or issuer is None or secret is None):
        if name is None:
            rprint(Text("Name (unique identifier):", style="cyan"))
            name = typer.prompt("")

        if issuer is None:
            rprint(Text("Issuer:", style="cyan"))
            issuer = typer.prompt("")

        if secret is None:
            rprint(Text("Secret:", style="cyan"))
            secret = typer.prompt("")

        commands.add_entry_interactive(name, issuer, secret, ctx)
        return

    if name is None or issuer is None or secret is None:
        helpers.print_error("Missing arguments: NAME, ISSUER and SECRET are required")
        rprint("Usage: d2fa add NAME ISSUER SECRET")
        rprint("Example: d2fa add GitHub GitHub ABCDEFGHIJKL1234")
        raise typer.Exit(1)

    commands.add_entry(name, issuer, secret, ctx)


@app.command("code")
def code_cmd(ctx: typer.Context, name: str) -> None:
    """Generate and display the TOTP code for an entry.

    Args:
        ctx: Typer context object containing configuration.
        name: Name of the entry to generate code for.
    """
    commands.generate_code(name, ctx)


@app.command("remove")
def remove_cmd(ctx: typer.Context, name: str) -> None:
    """Remove a TOTP entry from the vault.

    Args:
        ctx: Typer context object containing configuration.
        name: Name of the entry to remove.
    """
    commands.remove_entry(name, ctx)


@app.command("rename")
def rename_cmd(ctx: typer.Context, old: str, new: str) -> None:
    """Rename a TOTP entry in the vault.

    Args:
        ctx: Typer context object containing configuration.
        old: Current name of the entry.
        new: New name for the entry.
    """
    commands.rename_entry(old, new, ctx)


@app.command("export")
def export_cmd(ctx: typer.Context, path: str) -> None:
    """Export the vault to a JSON file.

    Args:
        ctx: Typer context object containing configuration.
        path: File path to export the vault to.
    """
    commands.export_vault(path, ctx)


@app.command("import")
def import_cmd(
    ctx: typer.Context,
    source: str,
    force: bool = typer.Option(False, "--force", help="Overwrite existing vault"),
) -> None:
    """Import entries from an external source.

    Args:
        ctx: Typer context object containing configuration.
        source: File path or URI to import from.
        force: Whether to overwrite existing vault.
    """
    commands.import_vault(source, force, ctx)


@app.command("backup")
def backup_cmd(ctx: typer.Context) -> None:
    """Create a backup of the vault."""
    commands.backup_vault(ctx)


@app.command("init-vault")
def init_vault_cmd(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", help="Overwrite existing vault"),
) -> None:
    """Initialize a new encrypted vault.

    Args:
        ctx: Typer context object containing configuration.
        force: Whether to overwrite existing vault.
    """
    commands.init_vault(force, ctx)
