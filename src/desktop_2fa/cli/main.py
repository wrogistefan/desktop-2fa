"""CLI main entry point for Desktop 2FA."""

import typer

from desktop_2fa import __version__

from .commands import (
    add_entry,
    backup_vault,
    export_vault,
    generate_code,
    import_vault,
    list_entries,
    remove_entry,
    rename_entry,
)

app = typer.Typer(help="Desktop‑2FA — secure offline TOTP authenticator")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(None, "--version", help="Show version and exit"),
) -> None:
    """Print version when no command is provided or when --version is used."""
    if version or ctx.invoked_subcommand is None:
        print(f"Desktop-2FA v{__version__}")
        raise typer.Exit()


@app.command("list")
def list_cmd() -> None:
    """List all entries in the vault."""
    list_entries()


@app.command("add")
def add_cmd(
    issuer: str = typer.Argument(None, help="Service provider name"),
    secret: str = typer.Argument(None, help="TOTP secret"),
) -> None:
    """Add a new TOTP entry."""
    if issuer is None:
        issuer = typer.prompt("Service provider name")
    if secret is None:
        secret = typer.prompt("TOTP secret", hide_input=True)
    add_entry(issuer=issuer, secret=secret)


@app.command("code")
def code_cmd(name: str) -> None:
    """Generate a TOTP code for the given entry."""
    generate_code(name)


@app.command("remove")
def remove_cmd(name: str) -> None:
    """Remove an entry by name."""
    remove_entry(name)


@app.command("rename")
def rename_cmd(old: str, new: str) -> None:
    """Rename an entry (changes name, not issuer)."""
    rename_entry(old, new)


@app.command("export")
def export_cmd(path: str) -> None:
    """Export vault to a JSON file."""
    export_vault(path)


@app.command("import")
def import_cmd(path: str) -> None:
    """Import vault from a JSON file."""
    import_vault(path)


@app.command("backup")
def backup_cmd() -> None:
    """Create a timestamped backup of the vault."""
    backup_vault()
