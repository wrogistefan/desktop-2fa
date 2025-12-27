import os

from desktop_2fa.crypto.aesgcm import decrypt, encrypt
from desktop_2fa.crypto.argon2 import derive_key


def test_encrypt_decrypt() -> None:
    salt = os.urandom(16)
    key = derive_key("password", salt)
    data = b"hello"
    enc = encrypt(key, data)
    dec = decrypt(key, enc)
    assert dec == data
