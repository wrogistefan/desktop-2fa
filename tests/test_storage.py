from desktop_2fa.vault.model import TokenEntry, VaultData
from desktop_2fa.vault.storage import deserialize, serialize


def test_roundtrip() -> None:
    v = VaultData(
        version=1, entries=[TokenEntry(name="Test", secret="ABC", issuer="X")]
    )
    raw = serialize(v)
    v2 = deserialize(raw)
    assert v2.entries[0].name == "Test"



