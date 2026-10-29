"""CLI stream contract, shared by early failures and command implementations."""

import json
import sys
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, NoReturn

import typer

from desktop_2fa.constants import ExitCode

if TYPE_CHECKING:
    from desktop_2fa.vault.models import TotpEntry


@dataclass(frozen=True)
class OutputMode:
    json: bool = False
    raw: bool = False
    quiet: bool = False


output_mode: ContextVar[OutputMode] = ContextVar("output_mode", default=OutputMode())


def diagnostic(message: str) -> None:
    """Write literal diagnostics to stderr; quiet suppresses both streams."""
    mode = output_mode.get()
    if not mode.quiet or mode.json:
        print(message, file=sys.stderr)


def failure(code: ExitCode, error: str, message: str) -> ExitCode:
    """JSON takes precedence over quiet when incompatible flags are supplied."""
    if output_mode.get().json:
        print(json.dumps({"error": error, "message": message}))
    else:
        diagnostic(message)
    return code


def fail(code: ExitCode, error: str, message: str) -> NoReturn:
    raise typer.Exit(failure(code, error, message))


DUPLICATE_WARNING = (
    "Warning: Your vault contains multiple entries with the same name. "
    "Run 'd2fa list --indices', then 'd2fa rename OLD NEW --index N' "
    "to select one entry."
)


def code_result(
    entry: "TotpEntry",
    code: str,
    remaining: int,
    *,
    copy: bool,
    copy_only: bool,
    clipboard_success: bool,
) -> None:
    """Render the unchanged code schema and human/automation success modes."""
    mode = output_mode.get()
    if mode.json:
        print(
            json.dumps(
                {
                    "account": entry.account_name,
                    "issuer": entry.issuer,
                    "code": code,
                    "valid_for": remaining,
                }
            )
        )
    elif mode.raw:
        print(code)
    elif not mode.quiet:
        if copy_only and clipboard_success:
            print(f"Code copied to clipboard (valid {remaining}s)")
        elif copy and clipboard_success:
            print(f"Copied to clipboard: {code} (valid {remaining}s)")
        else:
            print(f"{code} (valid {remaining}s)")
