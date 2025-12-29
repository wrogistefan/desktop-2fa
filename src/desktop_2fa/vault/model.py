from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TokenEntry:
    """Represents a TOTP token entry.

    Attributes:
        name: Optional display name for the entry.
        secret: Base32-encoded secret key.
        issuer: The service provider name.
        digits: Number of digits in the TOTP code (default 6).
        period: Time period in seconds (default 30).
        algorithm: Hash algorithm ('SHA1', 'SHA256', 'SHA512').
    """

    name: Optional[str]
    secret: str
    issuer: str
    digits: int = 6
    period: int = 30
    algorithm: str = "SHA1"


@dataclass
class VaultData:
    """Represents the vault data structure.

    Attributes:
        version: The vault format version.
        entries: List of TOTP token entries.
    """

    version: int
    entries: List[TokenEntry]
