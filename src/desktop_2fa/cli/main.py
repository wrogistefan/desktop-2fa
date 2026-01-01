"""CLI main entry point for Desktop 2FA."""

import os
import sys

import typer

from desktop_2fa import __version__

from . import commands
from .helpers import get_password_from_cli


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
) -> None:
    """
    Global CLI callback — initializes context and handles --version and no-args case.

    Contract (from tests):
    - `desktop-2fa --version` → prints version, exit 0
    - `desktop-2fa` (no command) → prints version, exit 0
    - any command → ctx.obj must be initialized and no early exit
    """

    # ZAWSZE inicjalizujemy ctx.obj – niezależnie od komendy / opcji
    ctx.obj = {
        "password": password,
        "password_file": password_file,
        "interactive": is_interactive(),
    }

    # Jeśli użytkownik podał --version LUB nie podał żadnej komendy,
    # zachowujemy się jak "print version and exit".
    # invoke_without_command=True gwarantuje, że callback jest wywołany także bez komendy.
    if version or ctx.invoked_subcommand is None:
        print(f"Desktop-2FA v{__version__}")
        raise typer.Exit()


@app.command("list")
def list_cmd(ctx: typer.Context) -> None:
    password = get_password_from_cli(ctx)
    commands.list_entries(password)


@app.command("add")
def add_cmd(
    ctx: typer.Context,
    issuer: str,
    secret: str,
) -> None:
    password = get_password_from_cli(ctx)
    commands.add_entry(issuer, secret, password)


@app.command("code")
def code_cmd(ctx: typer.Context, name: str) -> None:
    password = get_password_from_cli(ctx)
    commands.generate_code(name, password)


@app.command("remove")
def remove_cmd(ctx: typer.Context, name: str) -> None:
    password = get_password_from_cli(ctx)
    commands.remove_entry(name, password)


@app.command("rename")
def rename_cmd(ctx: typer.Context, old: str, new: str) -> None:
    password = get_password_from_cli(ctx)
    commands.rename_entry(old, new, password)


@app.command("export")
def export_cmd(ctx: typer.Context, path: str) -> None:
    password = get_password_from_cli(ctx)
    commands.export_vault(path, password)


@app.command("import")
def import_cmd(ctx: typer.Context, source: str) -> None:
    password = get_password_from_cli(ctx)
    commands.import_vault(source, password)


@app.command("backup")
def backup_cmd(ctx: typer.Context) -> None:
    password = get_password_from_cli(ctx)
    commands.backup_vault(password)
