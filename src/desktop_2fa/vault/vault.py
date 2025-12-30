"""Vault implementation for storing and managing TOTP entries."""

import os
from pathlib import Path
from typing import Optional

from ..crypto.aesgcm import decrypt, encrypt
from ..crypto.argon2 import derive_key
from .models import TotpEntry, VaultData


class Vault:
    """Vault using Pydantic models for validation and structure."""

    def __init__(self, data: Optional[VaultData] = None):
        """Initialize the vault with optional data.

        Args:
            data: The vault data to initialize with.
        """
        self.data = data or VaultData()

    @property
    def entries(self) -> list[TotpEntry]:
        """Get the list of TOTP entries.

        Returns:
            The list of TOTP entries.
        """
        return self.data.entries

    def add_entry(self, issuer: str, secret: str, account_name: Optional[str] = None) -> None:
        """Add a new TOTP entry to the vault.

        Args:
            issuer: The issuer name.
            secret: The base32-encoded secret.
            account_name: The account name (defaults to issuer).
        """
        if account_name is None:
            account_name = issuer

        entry = TotpEntry(
            issuer=issuer,
            account_name=account_name,
            secret=secret,
        )
        self.data.entries.append(entry)

    def get_entry(self, issuer: str) -> TotpEntry:
        """Get a TOTP entry by issuer or account name.

        Args:
            issuer: The issuer or account name to search for.

        Returns:
            The matching TOTP entry.

        Raises:
            ValueError: If no entry is found.
        """
        for entry in self.entries:
            if entry.issuer == issuer or entry.account_name == issuer:
                return entry
        raise ValueError(f"Entry '{issuer}' not found")

    def remove_entry(self, issuer: str) -> None:
        """Remove a TOTP entry by issuer or account name.

        Args:
            issuer: The issuer or account name of the entry to remove.
        """
        entry = self.get_entry(issuer)
        self.data.entries.remove(entry)

    @classmethod
    def load(cls, path: str | Path, password: str = "password") -> "Vault":
        """Load a vault from a file.

        Args:
            path: The file path to load from.
            password: The password to decrypt the vault.

        Returns:
            The loaded Vault instance.
        """
        if not os.path.exists(path):
            return cls()

        with open(path, "rb") as f:
            blob = f.read()

        salt, encrypted = blob[:16], blob[16:]
        key = derive_key(password, salt)
        raw_json = decrypt(key, encrypted)

        data = VaultData.model_validate_json(raw_json)
        return cls(data)

    def save(self, path: str | Path, password: str = "password") -> None:
        """Save the vault to a file.

        Args:
            path: The file path to save to.
            password: The password to encrypt the vault.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        salt = os.urandom(16)
        key = derive_key(password, salt)

        raw_json = self.data.model_dump_json().encode("utf-8")
        encrypted = encrypt(key, raw_json)

        with open(path, "wb") as f:
            f.write(salt + encrypted)
