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
    issuer: str | None = typer.Argument(None, help="Service provider name"),
    secret: str | None = typer.Argument(None, help="TOTP secret"),
) -> None:
    """Add a new TOTP entry."""
    prompted = False
    if issuer is None:
        issuer = typer.prompt("Service provider name")
        prompted = True

    assert issuer is not None

    while True:
        current_secret = secret
        if current_secret is None:
            current_secret = typer.prompt("TOTP secret:", hide_input=False)
            prompted = True
        if not current_secret.strip():
            print("Secret cannot be empty. Please enter a Base32 secret.")
            secret = None
            continue
        if prompted:
            print(f"You entered: {current_secret}")
            if not typer.confirm("Is this correct?", default=False):
                secret = None
                continue

        # Check for suspicious secret
        def is_repetitive(s: str) -> bool:
            n = len(s)
            for i in range(1, n // 2 + 1):
                if n % i == 0:
                    pattern = s[:i]
                    if pattern * (n // i) == s:
                        return True
            return False

        if len(current_secret) > 40 or is_repetitive(current_secret):
            if prompted and not typer.confirm(
                "This secret looks unusually long or repetitive. Did you paste it multiple times?",
                default=False,
            ):
                secret = None
                continue
        secret = current_secret
        break

    assert secret is not None

    try:
        add_entry(issuer=issuer, secret=secret)
        print(f"Added TOTP entry for {issuer}")
    except Exception as e:
        print(f"Error: {e}")


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
