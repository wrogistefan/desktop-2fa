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
    """Manages a collection of TOTP token entries with encryption."""

    def __init__(self, data: Optional[VaultData] = None):
        """Initialize the vault.

        Args:
            data: Optional VaultData, creates empty vault if None.
        """
        if data is None:
            data = VaultData(version=1, entries=[])
        self.data = data

    @property
    def entries(self) -> List[TokenEntry]:
        """Get the list of token entries."""
        return self.data.entries

    def add_entry(self, name: str, secret: str, issuer: Optional[str] = None) -> None:
        """Add a new token entry to the vault.

        Args:
            name: Display name for the entry.
            secret: Base32-encoded secret key.
            issuer: Service provider name (defaults to name if None).
        """
        if issuer is None:
            issuer = name
        entry = TokenEntry(name=name, secret=secret, issuer=issuer)
        self.data.entries.append(entry)

    def get_entry(self, name: str) -> TokenEntry:
        """Get a token entry by name.

        Args:
            name: The name of the entry.

        Returns:
            The TokenEntry instance.

        Raises:
            ValueError: If no entry with the given name exists.
        """
        for entry in self.entries:
            if entry.name == name:
                return entry
        raise ValueError(f"Entry with name '{name}' not found")

    def remove_entry(self, name: str) -> None:
        """Remove a token entry by name.

        Args:
            name: The name of the entry to remove.

        Raises:
            ValueError: If no entry with the given name exists.
        """
        entry = self.get_entry(name)
        self.data.entries.remove(entry)

    def to_json(self) -> Dict[str, Any]:
        """Convert the vault to a JSON-serializable dictionary.

        Returns:
            Dictionary representation of the vault.
        """
        return {
            "version": self.data.version,
            "entries": [entry.__dict__ for entry in self.entries],
        }

    @classmethod
    def load(cls, path: str, password: str = "password") -> "Vault":
        """Load and decrypt a vault from file.

        Args:
            path: Path to the vault file.
            password: Password for decryption (default for testing).

        Returns:
            The loaded Vault instance.
        """
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
        """Encrypt and save the vault to file.

        Creates a backup if the file already exists.

        Args:
            path: Path to save the vault file.
            password: Password for encryption (default for testing).
        """
        if os.path.exists(path):
            backup_path = str(path).replace(".bin", ".backup.bin")
            os.rename(path, backup_path)

        salt = os.urandom(16)
        key = derive_key(password, salt)
        raw = serialize(self.data)
        encrypted = encrypt(key, raw)

        with open(path, "wb") as f:
            f.write(salt + encrypted)
