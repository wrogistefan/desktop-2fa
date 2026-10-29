"""Exit-status mapping for expected CLI failures; messages exclude key material."""

from collections.abc import Callable
from functools import wraps
from inspect import signature
from typing import NoReturn, ParamSpec, TypeVar

import typer

from desktop_2fa.constants import ExitCode
from desktop_2fa.utils.base32 import InvalidSecret
from desktop_2fa.vault.vault import (
    AmbiguousEntry,
    CorruptedVault,
    EntryAlreadyExists,
    EntryNotFound,
    EntryRenameError,
    InvalidPassword,
    PermissionDenied,
    UnsupportedFormat,
    VaultError,
    VaultIOError,
    VaultNotFound,
    VaultValidationError,
)

from .output import OutputMode, failure, output_mode

CLI_ERRORS = (VaultError, ValueError, OSError)
P = ParamSpec("P")
R = TypeVar("R")


def describe_error(error: Exception) -> tuple[ExitCode, str, str]:
    """Classify by exception type, never by text that may include user data."""
    if isinstance(error, InvalidPassword):
        return ExitCode.INVALID_PASSWORD, "invalid_password", "Invalid vault password."
    if isinstance(error, VaultNotFound):
        return ExitCode.VAULT_MISSING, "vault_missing", "No vault found."
    if isinstance(error, EntryNotFound):
        return ExitCode.ENTRY_NOT_FOUND, "entry_not_found", str(error)
    if isinstance(error, (PermissionDenied, PermissionError)):
        return (
            ExitCode.GENERAL_ERROR,
            "permission_denied",
            "Cannot access vault directory (permission denied).",
        )
    if isinstance(error, CorruptedVault):
        return ExitCode.GENERAL_ERROR, "corrupted_vault", "Vault file is corrupted."
    if isinstance(error, UnsupportedFormat):
        return (
            ExitCode.GENERAL_ERROR,
            "unsupported_format",
            "Vault file format is unsupported.",
        )
    if isinstance(error, (VaultIOError, OSError)):
        return ExitCode.GENERAL_ERROR, "vault_io_error", "Failed to access vault file."
    if isinstance(error, AmbiguousEntry):
        return ExitCode.VALIDATION_ERROR, "entry_ambiguous", str(error)
    if isinstance(error, InvalidSecret):
        return (
            ExitCode.VALIDATION_ERROR,
            "invalid_secret",
            "Invalid TOTP secret. Add a valid replacement from the provider before removing the legacy entry.",
        )
    if isinstance(error, (EntryAlreadyExists, EntryRenameError, VaultValidationError)):
        return ExitCode.VALIDATION_ERROR, "validation_error", str(error)
    # Pydantic and unclassified ValueErrors can embed passwords/secrets in their
    # text. Report a generic validation failure rather than echoing that text.
    if isinstance(error, ValueError):
        return ExitCode.VALIDATION_ERROR, "validation_error", "Invalid input."
    return ExitCode.GENERAL_ERROR, "operation_failed", "Operation failed."


def report_error(
    error: Exception, *, json_mode: bool = False, quiet: bool = False
) -> ExitCode:
    """Report an expected failure and return its non-zero status."""
    code, err_id, message = describe_error(error)
    current = output_mode.get()
    token = output_mode.set(
        OutputMode(
            json=json_mode or current.json,
            raw=current.raw,
            quiet=quiet or current.quiet,
        )
    )
    try:
        return failure(code, err_id, message)
    finally:
        output_mode.reset(token)


def exit_for_error(
    error: Exception, *, json_mode: bool = False, quiet: bool = False
) -> NoReturn:
    """Report an expected failure and always terminate with its non-zero status."""
    raise typer.Exit(report_error(error, json_mode=json_mode, quiet=quiet)) from None


def command_errors(function: Callable[P, R]) -> Callable[P, R]:
    """Catch expected failures outside operation-specific error handlers."""

    parameters = signature(function)

    @wraps(function)
    def guarded(*args: P.args, **kwargs: P.kwargs) -> R:
        token = None
        if "json_mode" in parameters.parameters:
            bound = parameters.bind_partial(*args, **kwargs).arguments
            token = output_mode.set(
                OutputMode(
                    json=bool(bound.get("json_mode", False)),
                    raw=bool(bound.get("raw", False)),
                    quiet=bool(bound.get("quiet", False)),
                )
            )
        try:
            return function(*args, **kwargs)
        except typer.Exit:
            raise
        except (typer.Abort, EOFError, KeyboardInterrupt):
            from .output import fail

            fail(ExitCode.VALIDATION_ERROR, "input_aborted", "Input cancelled.")
        except CLI_ERRORS as error:
            exit_for_error(error)
        except Exception as error:
            # The CLI boundary must not expose traceback locals/exception text
            # from unexpected failures. Domain APIs still propagate exceptions.
            exit_for_error(error)
        finally:
            if token is not None:
                output_mode.reset(token)

    return guarded
