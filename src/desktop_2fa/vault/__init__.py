"""Desktop 2FA vault management package."""

from .models import TotpEntry, VaultData
from .vault import AmbiguousEntry, Vault

__all__ = ["AmbiguousEntry", "TotpEntry", "VaultData", "Vault"]
