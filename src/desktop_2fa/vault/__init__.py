"""Desktop 2FA vault management package."""

from .models import TotpEntry, VaultData
from .vault import AmbiguousEntry, EntryRenameError, Vault, VaultValidationError

__all__ = [
    "AmbiguousEntry",
    "EntryRenameError",
    "TotpEntry",
    "VaultData",
    "Vault",
    "VaultValidationError",
]
