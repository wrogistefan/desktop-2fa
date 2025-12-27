from dataclasses import dataclass
from typing import List


@dataclass
class TokenEntry:
    name: str
    secret: str
    issuer: str
    digits: int = 6
    period: int = 30
    algorithm: str = "SHA1"


@dataclass
class VaultData:
    version: int
    entries: List[TokenEntry]
