"""Desktop 2FA vault management package."""

from .models import TotpEntry, VaultData
from .vault import (
    AmbiguousEntry,
    EntryAlreadyExists,
    EntryNotFound,
    EntryRenameError,
    ExportRefused,
    Vault,
    VaultValidationError,
)

__all__ = [
    "AmbiguousEntry",
    "EntryAlreadyExists",
    "EntryNotFound",
    "EntryRenameError",
    "ExportRefused",
    "TotpEntry",
    "VaultData",
    "Vault",
    "VaultValidationError",
]
