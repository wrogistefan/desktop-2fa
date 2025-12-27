from typer import Typer

from .commands import add_entry, generate_code, list_entries

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
