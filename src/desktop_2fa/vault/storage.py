import json
from .model import VaultData, TokenEntry

def serialize(vault: VaultData) -> bytes:
    data = {
        "version": vault.version,
        "entries": [entry.__dict__ for entry in vault.entries],
    }
    return json.dumps(data).encode("utf-8")

def deserialize(raw: bytes) -> VaultData:
    data = json.loads(raw.decode("utf-8"))
    entries = [TokenEntry(**e) for e in data["entries"]]
    return VaultData(version=data["version"], entries=entries)
