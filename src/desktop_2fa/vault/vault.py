import os

from ..crypto.aesgcm import decrypt, encrypt
from ..crypto.argon2 import derive_key
from .model import VaultData
from .storage import deserialize, serialize


def save_vault(path: str, vault: VaultData, password: str) -> None:
    salt = os.urandom(16)
    key = derive_key(password, salt)
    raw = serialize(vault)
    encrypted = encrypt(key, raw)
    with open(path, "wb") as f:
        f.write(salt + encrypted)


def load_vault(path: str, password: str) -> VaultData:
    with open(path, "rb") as f:
        data = f.read()
    salt, encrypted = data[:16], data[16:]
    key = derive_key(password, salt)
    raw = decrypt(key, encrypted)
    return deserialize(raw)
