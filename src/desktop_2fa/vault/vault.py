"""Vault implementation for storing and managing TOTP entries."""

import os
import stat
import tempfile
from pathlib import Path
from typing import Literal, Optional

from pydantic import ValidationError

from ..crypto.aesgcm import decrypt, encrypt
from ..crypto.argon2 import derive_key
from .models import TotpEntry, VaultData

# Vault file format constants
VAULT_MAGIC = b"D2FA"
VAULT_VERSION = b"\x01"
HEADER_LEN = len(VAULT_MAGIC) + len(VAULT_VERSION)
MAX_VAULT_SIZE = 10 * 1024 * 1024
# D2FA v1: header + salt + AES-GCM nonce + authentication tag.
VAULT_OVERHEAD = HEADER_LEN + 16 + 12 + 16


class VaultError(Exception):
    """Base exception for vault-related errors."""

    pass


class InvalidPassword(VaultError):
    """Raised when the provided password is incorrect."""

    pass


class VaultValidationError(VaultError, ValueError):
    """Raised when save output would exceed loader limits or fail validation."""


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


class AmbiguousEntry(ValueError):
    """Raised when a name cannot identify a single vault entry."""


class EntryRenameError(ValueError):
    """Raised for an occupied rename destination or an invalid entry selector."""


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
        *,
        algorithm: Literal["SHA1", "SHA256", "SHA512"] = "SHA1",
        digits: Literal[6, 7, 8] = 6,
        period: int = 30,
    ) -> None:
        """Add a new TOTP entry to the vault.

        Args:
            name: The unique account name.
            issuer: The issuer name.
            secret: The base32-encoded secret.
            algorithm: TOTP hash algorithm (default SHA1).
            digits: TOTP code length (default 6).
            period: TOTP period in seconds (default 30).
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
            algorithm=algorithm,
            digits=digits,
            period=period,
        )
        self.data.entries.append(entry)

    def rename_entry(self, old: str, new: str, *, index: int | None = None) -> None:
        """Update account name and issuer without creating duplicate names.

        Resolve old as an exact account name, then a unique issuer. An explicit
        one-based index into entries may select among matches at that same tier.
        Validate the selector and destination before mutating either field.
        Renaming a uniquely named entry to itself still updates its issuer.

        Raises:
            AmbiguousEntry: If old is ambiguous without an index.
            EntryRenameError: If the index is invalid or new is already occupied.
            ValueError: If old is not found.
        """
        if index is None:
            entry = self.get_entry(old)
        else:
            if type(index) is not int or not 1 <= index <= len(self.entries):
                raise EntryRenameError(
                    "Invalid entry index; use a number from 'd2fa list --indices'."
                )
            entry = self.entries[index - 1]
            if not any(entry is match for match in self._matching_entries(old)):
                raise EntryRenameError(
                    "Entry index does not match the old name at the selected "
                    "account/issuer tier; run 'd2fa list --indices' again."
                )

        if any(
            other is not entry and other.account_name == new for other in self.entries
        ):
            raise EntryRenameError(
                f'An entry with name "{new}" already exists. Choose a unique name.'
            )
        entry.account_name = new
        entry.issuer = new

    def _matching_entries(self, name: str) -> list[TotpEntry]:
        """Return matches at the first non-empty account-name/issuer tier."""
        matches = [entry for entry in self.entries if entry.account_name == name]
        return matches or [entry for entry in self.entries if entry.issuer == name]

    def get_entry(self, issuer: str) -> TotpEntry:
        """Resolve an exact account name, then a unique issuer fallback.

        Matching is case-sensitive. Exact account names take precedence over
        issuers regardless of entry order. Neither tier selects among duplicates.

        Args:
            issuer: The issuer or account name to search for.

        Returns:
            The matching TOTP entry.

        Raises:
            AmbiguousEntry: If multiple entries match at the selected tier.
            ValueError: If no entry is found.
        """
        matches = self._matching_entries(issuer)
        if len(matches) > 1:
            raise AmbiguousEntry(
                f"Ambiguous entry '{issuer}': multiple entries match. Operation aborted."
            )
        if matches:
            return matches[0]
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
    def load(cls, path: str | Path, password: str) -> "Vault":
        """Load a vault from a file.

        Args:
            path: The file path to load from.
            password: The non-empty password to decrypt the vault.

        Returns:
            The loaded Vault instance.

        Raises:
            TypeError: If password is not a string.
            ValueError: If password is empty.
            VaultIOError: If the vault file cannot be read due to IO errors.
            UnsupportedFormat: If the vault file format is invalid.
            InvalidPassword: If the password is incorrect.
            CorruptedVault: If the vault data is corrupted.
        """
        _validate_password(password)
        fd: int | None = None
        try:
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
            file_stat = os.fstat(fd)
            if not stat.S_ISREG(file_stat.st_mode):
                raise UnsupportedFormat("Vault path is not a regular file")

            with os.fdopen(fd, "rb") as f:
                fd = None
                blob = f.read(MAX_VAULT_SIZE + 1)
            if len(blob) > MAX_VAULT_SIZE:
                raise UnsupportedFormat("Vault file exceeds maximum supported size")
        except PermissionError:
            raise PermissionDenied(
                "Cannot access vault file (permission denied)"
            ) from None
        except FileNotFoundError:
            raise VaultNotFound("Vault file not found") from None
        except OSError as e:
            raise VaultIOError(f"Failed to read vault file: {e}") from None
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass

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
                "This was allowed in older versions. Run 'd2fa list --indices', "
                "then 'd2fa rename OLD NEW --index N' to select one entry."
            )

        return vault

    def save(self, path: str | Path, password: str) -> None:
        """Save the vault to a file.

        Args:
            path: The file path to save to.
            password: The non-empty password to encrypt the vault.

        Raises:
            TypeError: If password is not a string.
            ValueError: If password is empty.
            VaultValidationError: If data is invalid or output exceeds the
                loader's size limit.
            VaultIOError: If saving fails due to IO errors.
        """
        _validate_password(password)
        try:
            # Validate the exact snapshot to be encrypted, not mutable model
            # instances (Pydantic normally trusts already-created instances).
            # Suppress serialization warnings that could expose field values.
            raw_json = self.data.model_dump_json(warnings=False).encode("utf-8")
        except (ValueError, TypeError):
            raise VaultValidationError(
                "Vault data cannot be serialized; correct entries before saving."
            ) from None
        output_size = len(raw_json) + VAULT_OVERHEAD
        if output_size > MAX_VAULT_SIZE:
            raise VaultValidationError(
                f"Vault output exceeds maximum supported size of {MAX_VAULT_SIZE} "
                f"bytes (10 MiB): {output_size} bytes; reduce vault data before saving."
            )
        try:
            VaultData.model_validate_json(raw_json)
        except ValidationError:
            raise VaultValidationError(
                "Vault contains invalid data; correct entries before saving."
            ) from None

        path = Path(path)
        temp_path: Path | None = None
        fd: int | None = None

        try:
            # DEF-02: Moved mkdir inside try block to catch PermissionError
            path.parent.mkdir(parents=True, exist_ok=True)

            header = VAULT_MAGIC + VAULT_VERSION
            salt = os.urandom(16)

            key = derive_key(password, salt)

            encrypted = encrypt(key, raw_json)

            fd, temp_name = tempfile.mkstemp(
                prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
            )
            temp_path = Path(temp_name)
            with os.fdopen(fd, "wb") as f:
                fd = None
                f.write(header + salt + encrypted)
                f.flush()
                os.fsync(f.fileno())

            os.replace(temp_path, path)
            temp_path = None
        except PermissionError:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if temp_path is not None and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise PermissionDenied(
                "Cannot access vault directory (permission denied)"
            ) from None
        except OSError as e:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if temp_path is not None and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            error_msg = e.strerror if e.strerror else str(e)
            raise VaultIOError(f"Failed to save vault: {error_msg}") from None


def _validate_password(password: str) -> None:
    if not isinstance(password, str):
        raise TypeError("Password must be a string.")
    if not password:
        raise ValueError("Password cannot be empty.")
