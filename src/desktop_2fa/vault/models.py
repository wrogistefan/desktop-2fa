"""Pydantic models for vault data structures."""

import base64
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class TotpEntry(BaseModel):
    """Model representing a TOTP entry in the vault.

    Attributes:
        issuer: The service provider name (e.g., "GitHub").
        account_name: The account identifier (e.g., "user@example.com").
        secret: The Base32-encoded TOTP secret key.
        digits: Number of digits in the generated code (6, 7, or 8).
        period: Time period in seconds between code changes (default 30).
        algorithm: Hash algorithm used for TOTP generation (SHA1, SHA256, SHA512).
    """

    issuer: Optional[str] = Field(None)
    account_name: Optional[str] = Field(None)
    secret: str = Field(...)
    digits: Literal[6, 7, 8] = 6
    period: int = 30
    algorithm: Literal["SHA1", "SHA256", "SHA512"] = "SHA1"

    @field_validator("secret")
    @classmethod
    def validate_base32_secret(cls, v: str) -> str:
        """Validate that the secret is valid Base32.

        Args:
            v: The secret value to validate.

        Returns:
            The validated secret.

        Raises:
            ValueError: If the secret is not valid Base32.
        """
        try:
            base64.b32decode(v.upper())
        except Exception:
            raise ValueError("Invalid Base32 TOTP secret")
        return v

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: int) -> int:
        """Validate that the period is positive.

        Args:
            v: The period value to validate.

        Returns:
            The validated period.

        Raises:
            ValueError: If the period is not positive.
        """
        if v <= 0:
            raise ValueError("TOTP period must be positive")
        return v


class VaultData(BaseModel):
    """Model representing the vault data structure.

    Attributes:
        version: Vault format version (default 1).
        entries: List of TOTP entries in the vault.
    """

    version: int = 1
    entries: list[TotpEntry] = Field(default_factory=list)
