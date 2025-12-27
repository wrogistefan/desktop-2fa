from pathlib import Path

from typer import Typer

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

app = Typer(help="desktop-2fa CLI — local-first TOTP authenticator")


@app.command()
def list() -> None:
    """List all entries in the vault."""
    list_entries()


@app.command()
def add(issuer: str, secret: str) -> None:
    """Add a new TOTP entry."""
    add_entry(issuer, secret)


@app.command()
def code(issuer: str) -> None:
    """Generate a TOTP code for the given issuer."""
    generate_code(issuer)


@app.command()
def remove(issuer: str) -> None:
    """Remove an entry from the vault."""
    remove_entry(issuer)


@app.command()
def rename(old: str, new: str) -> None:
    """Rename an entry."""
    rename_entry(old, new)


@app.command()
def export(path: Path) -> None:
    """Export the encrypted vault to a file."""
    export_vault(str(path))


@app.command("import")
def import_cmd(path: Path) -> None:
    """Import a vault from a file."""
    import_vault(str(path))


@app.command()
def backup() -> None:
    """Create a timestamped backup of the vault."""
    backup_vault()
