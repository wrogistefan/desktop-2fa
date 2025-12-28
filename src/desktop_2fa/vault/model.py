from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TokenEntry:
    name: Optional[str]
    secret: str
    issuer: str
    digits: int = 6
    period: int = 30
    algorithm: str = "SHA1"


@dataclass
class VaultData:
    version: int
    entries: List[TokenEntry]
