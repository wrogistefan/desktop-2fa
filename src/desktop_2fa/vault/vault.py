import json
import os
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from ..crypto.aesgcm import decrypt, encrypt
from ..crypto.argon2 import derive_key
from .model import TokenEntry, VaultData


def serialize(data: Any) -> bytes:
    """Serialize data to bytes using JSON."""
    if isinstance(data, VaultData):
        dict_data = asdict(data)
    elif isinstance(data, dict):
        dict_data = data
    else:
        raise TypeError(f"Unsupported data type: {type(data)}")
    return json.dumps(dict_data).encode("utf-8")


def deserialize(blob: bytes) -> Any:
    """Deserialize bytes to data using JSON."""
    dict_data = json.loads(blob.decode("utf-8"))
    # For now, assume it's VaultData if it has 'version' and 'entries'
    if "version" in dict_data and "entries" in dict_data:
        entries = [TokenEntry(**e) for e in dict_data["entries"]]
        return VaultData(version=dict_data["version"], entries=entries)
    else:
        return dict_data


class Vault:
    def __init__(self, data: Optional[VaultData] = None):
        if data is None:
            data = VaultData(version=1, entries=[])
        self.data = data

    @property
    def entries(self) -> List[TokenEntry]:
        return self.data.entries

    def add_entry(self, name: str, secret: str, issuer: Optional[str] = None) -> None:
        if issuer is None:
            issuer = name
        entry = TokenEntry(name=name, secret=secret, issuer=issuer)
        self.data.entries.append(entry)

    def get_entry(self, name: str) -> TokenEntry:
        for entry in self.entries:
            if entry.name == name:
                return entry
        raise ValueError(f"Entry with name '{name}' not found")

    def remove_entry(self, name: str) -> None:
        entry = self.get_entry(name)
        self.data.entries.remove(entry)

    def to_json(self) -> Dict[str, Any]:
        return {
            "version": self.data.version,
            "entries": [entry.__dict__ for entry in self.entries],
        }

    @classmethod
    def load(cls, path: str, password: str = "password") -> "Vault":
        if not os.path.exists(path):
            return cls(VaultData(version=1, entries=[]))

        with open(path, "rb") as f:
            data = f.read()

        salt, encrypted = data[:16], data[16:]
        key = derive_key(password, salt)
        raw = decrypt(key, encrypted)
        vault_data = deserialize(raw)

        # Migration: ensure name exists
        for entry in vault_data.entries:
            if not getattr(entry, "name", None):
                entry.name = entry.issuer

        return cls(vault_data)

    def save(self, path: str, password: str = "password") -> None:
        if os.path.exists(path):
            backup_path = str(path).replace(".bin", ".backup.bin")
            os.rename(path, backup_path)

        salt = os.urandom(16)
        key = derive_key(password, salt)
        raw = serialize(self.data)
        encrypted = encrypt(key, raw)

        with open(path, "wb") as f:
            f.write(salt + encrypted)
