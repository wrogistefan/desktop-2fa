import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt(key: bytes, data: bytes) -> bytes:
    aes = AESGCM(key)
    nonce = os.urandom(12)
    return nonce + aes.encrypt(nonce, data, None)


def decrypt(key: bytes, blob: bytes) -> bytes:
    nonce, ciphertext = blob[:12], blob[12:]
    aes = AESGCM(key)
    return aes.decrypt(nonce, ciphertext, None)
