"""AES-GCM encryption and decryption utilities."""

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt(key: bytes, data: bytes) -> bytes:
    """Encrypt data using AES-GCM.

    Args:
        key: The encryption key (32 bytes for AES-256).
        data: The plaintext data to encrypt.

    Returns:
        The encrypted data in the format: 12-byte nonce + ciphertext + 16-byte authentication tag.
    """
    aes = AESGCM(key)
    nonce = os.urandom(12)
    return nonce + aes.encrypt(nonce, data, None)


def decrypt(key: bytes, blob: bytes) -> bytes:
    """Decrypt data using AES-GCM.

    Args:
        key: The decryption key (32 bytes for AES-256).
        blob: The encrypted data in the format: 12-byte nonce + ciphertext + 16-byte authentication tag.

    Returns:
        The decrypted plaintext data.

    Raises:
        ValueError: If decryption fails.
    """
    if len(blob) < 12:
        raise ValueError("Encrypted blob too short")
    nonce, ciphertext = blob[:12], blob[12:]
    aes = AESGCM(key)
    try:
        return aes.decrypt(nonce, ciphertext, None)
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}") from e
