"""Constants for Desktop 2FA."""

from enum import IntEnum


class ExitCode(IntEnum):
    """Exit codes for the application."""

    SUCCESS = 0
    GENERAL_ERROR = 1
    VAULT_MISSING = 4
    CLIPBOARD_UNAVAILABLE = 5
    VALIDATION_ERROR = 6