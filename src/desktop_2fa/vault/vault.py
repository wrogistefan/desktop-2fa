import os
from typing import List

from ..crypto.aesgcm import decrypt, encrypt
from ..crypto.argon2 import derive_key
from .model import TokenEntry, VaultData
from .storage import deserialize, serialize


class Vault:
    def __init__(self, data: VaultData):
        self.data = data

    @property
    def entries(self) -> List[TokenEntry]:
        return self.data.entries

    def add_entry(self, issuer: str, secret: str) -> None:
        from .model import TokenEntry

        entry = TokenEntry(name=issuer, secret=secret, issuer=issuer)
        self.data.entries.append(entry)

    def get_entry(self, issuer: str) -> TokenEntry:
        for entry in self.entries:
            if entry.issuer == issuer:
                return entry
        raise ValueError(f"Entry for issuer '{issuer}' not found")

    @classmethod
    def load(cls, path: str, password: str = "password") -> "Vault":
        if not os.path.exists(path):
            return cls(VaultData(version=1, entries=[]))
        with open(path, "rb") as f:
            data = f.read()
        salt, encrypted = data[:16], data[16:]
        key = derive_key(password, salt)
        raw = decrypt(key, encrypted)
        vault_data = deserialize(raw)
        return cls(vault_data)

    def save(self, path: str, password: str = "password") -> None:
        salt = os.urandom(16)
        key = derive_key(password, salt)
        raw = serialize(self.data)
        encrypted = encrypt(key, raw)
        with open(path, "wb") as f:
            f.write(salt + encrypted)


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
