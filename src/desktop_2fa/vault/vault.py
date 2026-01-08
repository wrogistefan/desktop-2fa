"""Vault implementation for storing and managing TOTP entries."""

import os
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from ..crypto.aesgcm import decrypt, encrypt
from ..crypto.argon2 import derive_key
from .models import TotpEntry, VaultData

# Vault file format constants
VAULT_MAGIC = b"D2FA"
VAULT_VERSION = b"\x01"
HEADER_LEN = len(VAULT_MAGIC) + len(VAULT_VERSION)


class VaultError(Exception):
    """Base exception for vault-related errors."""

    pass


class InvalidPassword(VaultError):
    """Raised when the provided password is incorrect."""

    pass


class CorruptedVault(VaultError):
    """Raised when the vault file is corrupted or contains invalid data."""

    pass


class UnsupportedFormat(VaultError):
    """Raised when the vault file format is unsupported or invalid."""

    pass


class VaultIOError(VaultError):
    """Raised for filesystem or IO-related errors."""

    pass


class PermissionDenied(VaultIOError):
    """Raised when the user lacks permission to access the vault."""

    pass


class VaultNotFound(VaultIOError):
    """Raised when the vault file does not exist."""

    pass


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

    def add_entry(
        self,
        name: str,
        issuer: str,
        secret: str,
    ) -> None:
        """Add a new TOTP entry to the vault.

        Args:
            name: The unique account name.
            issuer: The issuer name.
            secret: The base32-encoded secret.
        """
        # Check for duplicate names
        for entry in self.entries:
            if entry.account_name == name:
                raise ValueError(
                    f'An entry with name "{name}" already exists. Names must be unique.'
                )

        entry = TotpEntry(
            account_name=name,
            issuer=issuer,
            secret=secret,
        )
        self.data.entries.append(entry)

    def rename_entry(self, old: str, new: str) -> None:
        """Rename an entry (placeholder for future implementation)."""
        raise NotImplementedError("rename will be implemented in a future version")

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

    def find_entries(self, name: str) -> list[TotpEntry]:
        """Find all entries matching the given name (issuer or account_name).

        Args:
            name: The issuer or account name to search for.

        Returns:
            List of matching entries.
        """
        matches = []
        for entry in self.entries:
            if entry.issuer == name or entry.account_name == name:
                matches.append(entry)
        return matches

    def remove_entry(self, issuer: str) -> None:
        """Remove a TOTP entry by issuer or account name.

        Args:
            issuer: The issuer or account name of the entry to remove.
        """
        entry = self.get_entry(issuer)
        self.data.entries.remove(entry)

    @classmethod
    def load(cls, path: str | Path, password: Optional[str] = None) -> "Vault":
        """Load a vault from a file.

        Args:
            path: The file path to load from.
            password: The password to decrypt the vault. If None, a default
                internal password is used (for "no-password" vaults).

        Returns:
            The loaded Vault instance.

        Raises:
            VaultIOError: If the vault file cannot be read due to IO errors.
            UnsupportedFormat: If the vault file format is invalid.
            InvalidPassword: If the password is incorrect.
            CorruptedVault: If the vault data is corrupted.
        """
        try:
            with open(path, "rb") as f:
                blob = f.read()
        except PermissionError:
            raise PermissionDenied(
                "Cannot access vault file (permission denied)"
            ) from None
        except FileNotFoundError:
            raise VaultNotFound("Vault file not found") from None
        except OSError as e:
            raise VaultIOError(f"Failed to read vault file: {e}") from None

        if len(blob) < HEADER_LEN + 16:
            raise UnsupportedFormat("Vault file is too short or invalid format")

        # Check magic header and version
        if blob[:4] != VAULT_MAGIC:
            raise UnsupportedFormat("Invalid vault file format: incorrect magic header")
        if blob[4:5] != VAULT_VERSION:
            raise UnsupportedFormat("Unsupported vault file version")

        # First 5 bytes: header, next 16: salt, rest: AES-GCM blob (nonce + ciphertext + tag)
        salt, encrypted = blob[HEADER_LEN : HEADER_LEN + 16], blob[HEADER_LEN + 16 :]

        if len(encrypted) == 0:
            raise UnsupportedFormat("Vault file is invalid: empty encrypted blob")

        # For "no-password" vaults we consistently use an empty password string.
        if password is None:
            password = ""

        key = derive_key(password, salt)
        try:
            raw_json = decrypt(key, encrypted)
        except ValueError as e:
            raise InvalidPassword("Invalid password or corrupted vault") from e

        # decrypt() returns bytes; Pydantic v2 accepts bytes as JSON input.
        try:
            data = VaultData.model_validate_json(raw_json)
        except ValidationError as e:
            # If Pydantic validation fails, it's corrupted data (not a password issue)
            # because the decryption succeeded but the data structure is wrong
            raise CorruptedVault("Vault contains invalid data") from e

        vault = cls(data)

        # Check for duplicate account names and warn
        names = [entry.account_name for entry in vault.entries if entry.account_name]
        duplicates = [name for name in set(names) if names.count(name) > 1]
        if duplicates:
            print(
                f"Warning: Your vault contains multiple entries with the same name: {', '.join(chr(34) + name + chr(34) for name in duplicates)}."
            )
            print(
                "This was allowed in older versions. You can resolve this by renaming entries using the rename command."
            )

        return vault

    def save(self, path: str | Path, password: Optional[str] = None) -> None:
        """Save the vault to a file.

        Args:
            path: The file path to save to.
            password: The password to encrypt the vault. If None, a default
                internal password is used (for "no-password" vaults).

        Raises:
            VaultIOError: If saving fails due to IO errors.
        """
        path = Path(path)
        temp_path = path.with_suffix(".tmp")

        try:
            # DEF-02: Moved mkdir inside try block to catch PermissionError
            path.parent.mkdir(parents=True, exist_ok=True)

            header = VAULT_MAGIC + VAULT_VERSION
            salt = os.urandom(16)

            # For "no-password" vaults we consistently use an empty password string.
            if password is None:
                password = ""

            key = derive_key(password, salt)

            raw_json = self.data.model_dump_json().encode("utf-8")
            encrypted = encrypt(key, raw_json)

            fd = os.open(str(temp_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(header + salt + encrypted)
                    f.flush()
                    os.fsync(fd)
            except OSError:
                os.close(fd)
                raise

            os.replace(temp_path, path)
        except PermissionError:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise PermissionDenied(
                "Cannot access vault directory (permission denied)"
            ) from None
        except OSError as e:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            error_msg = e.strerror if e.strerror else str(e)
            raise VaultIOError(f"Failed to save vault: {error_msg}") from None
