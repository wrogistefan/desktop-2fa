"""AES-GCM encryption and decryption utilities."""

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt(key: bytes, data: bytes) -> bytes:
    """Encrypt data using AES-GCM.

    Args:
        key: The encryption key (32 bytes for AES-256).
        data: The plaintext data to encrypt.

    Returns:
        The encrypted data with nonce prepended.
    """
    aes = AESGCM(key)
    nonce = os.urandom(12)
    return nonce + aes.encrypt(nonce, data, None)


def decrypt(key: bytes, blob: bytes) -> bytes:
    """Decrypt data using AES-GCM.

    Args:
        key: The decryption key (32 bytes for AES-256).
        blob: The encrypted data with nonce prepended.

    Returns:
        The decrypted plaintext data.
    """
    nonce, ciphertext = blob[:12], blob[12:]
    aes = AESGCM(key)
    try:
        return aes.decrypt(nonce, ciphertext, None)
    except Exception as e:
        raise Exception(f"Decryption failed: {e}") from e
