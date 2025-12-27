from ..crypto.aesgcm import encrypt, decrypt
from ..crypto.argon2 import derive_key
from .storage import serialize, deserialize
from .model import VaultData

def save_vault(path: str, vault: VaultData, password: str) -> None:
    key, salt = derive_key(password)
    raw = serialize(vault)
    encrypted = encrypt(key, raw)
    with open(path, "wb") as f:
        f.write(salt + encrypted)

def load_vault(path: str, password: str) -> VaultData:
    with open(path, "rb") as f:
        data = f.read()
    salt, encrypted = data[:16], data[16:]
    key, _ = derive_key(password, salt=salt)
    raw = decrypt(key, encrypted)
    return deserialize(raw)
