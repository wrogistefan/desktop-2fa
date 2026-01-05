import os

import pytest

from desktop_2fa.crypto.aesgcm import decrypt, encrypt
from desktop_2fa.crypto.argon2 import derive_key


def test_encrypt_decrypt() -> None:
    salt = os.urandom(16)
    key = derive_key("password", salt)
    data = b"hello"
    enc = encrypt(key, data)
    dec = decrypt(key, enc)
    assert dec == data


def test_decrypt_corrupted_ciphertext() -> None:
    salt = os.urandom(16)
    key = derive_key("password", salt)
    data = b"hello"
    enc = encrypt(key, data)

    # Corrupt the ciphertext by flipping a bit
    corrupted = bytearray(enc)
    corrupted[10] ^= 0xFF

    with pytest.raises(ValueError):
        decrypt(key, bytes(corrupted))


def test_encrypt_decrypt_empty_data() -> None:
    salt = os.urandom(16)
    key = derive_key("password", salt)
    data = b""
    enc = encrypt(key, data)
    dec = decrypt(key, enc)
    assert dec == data


def test_encrypt_decrypt_large_data() -> None:
    salt = os.urandom(16)
    key = derive_key("password", salt)
    data = b"x" * 10000  # 10KB of data
    enc = encrypt(key, data)
    dec = decrypt(key, enc)
    assert dec == data


def test_decrypt_too_short_blob() -> None:
    salt = os.urandom(16)
    key = derive_key("password", salt)

    with pytest.raises(ValueError, match="Encrypted blob too short"):
        decrypt(key, b"short")
