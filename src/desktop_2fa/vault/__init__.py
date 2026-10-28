"""Desktop 2FA vault management package."""

from .models import TotpEntry, VaultData
from .vault import (
    AmbiguousEntry,
    EntryAlreadyExists,
    EntryNotFound,
    EntryRenameError,
    Vault,
    VaultValidationError,
)

__all__ = [
    "AmbiguousEntry",
    "EntryAlreadyExists",
    "EntryNotFound",
    "EntryRenameError",
    "TotpEntry",
    "VaultData",
    "Vault",
    "VaultValidationError",
]
