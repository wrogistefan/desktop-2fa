import json
from pathlib import Path
from typing import Any, Dict, List

from .vault.model import TokenEntry, VaultData


class Storage:
    def __init__(self, entries: List[TokenEntry]):
        self.data = VaultData(version=1, entries=entries)

    @property
    def entries(self) -> List[TokenEntry]:
        return self.data.entries

    @entries.setter
    def entries(self, value: List[TokenEntry]) -> None:
        self.data.entries = value

    def add_entry(self, issuer: str, secret: str) -> None:
        entry = TokenEntry(name=issuer, secret=secret, issuer=issuer)
        self.data.entries.append(entry)

    def get_entry(self, issuer: str) -> TokenEntry:
        for entry in self.entries:
            if entry.issuer == issuer:
                return entry
        raise ValueError(f"Entry for issuer '{issuer}' not found")

    def remove_entry(self, issuer: str) -> None:
        entry = self.get_entry(issuer)
        self.data.entries.remove(entry)

    def to_json(self) -> Dict[str, Any]:
        return {
            "version": self.data.version,
            "entries": [entry.__dict__ for entry in self.entries],
        }

    @classmethod
    def load(cls, path: str) -> "Storage":
        if not Path(path).exists():
            return cls([])
        with open(path, "r") as f:
            data = json.load(f)
        entries = []
        for e in data["entries"]:
            entry = TokenEntry(
                name=e.get("name", e["issuer"]),
                secret=e["secret"],
                issuer=e["issuer"],
                digits=e.get("digits", 6),
                period=e.get("period", 30),
                algorithm=e.get("algorithm", "SHA1"),
            )
            entries.append(entry)
        return cls(entries)

    def save(self, path: str) -> None:
        data = self.to_json()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
