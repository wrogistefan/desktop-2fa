from pathlib import Path

import pytest

from desktop_2fa.vault.vault import Vault, deserialize, serialize


def test_vault_roundtrip(tmp_path: Path) -> None:
    """Vault zapis → odczyt → zgodność danych."""
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("GitHub", "JBSWY3DPEHPK3PXP")
    vault.save(str(path))

    loaded = Vault.load(str(path))
    assert loaded.get_entry("GitHub").secret == "JBSWY3DPEHPK3PXP"


def test_vault_is_binary(tmp_path: Path) -> None:
    """Plik vaulta musi być binarny, nie JSON."""
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("Test", "AAAAA")
    vault.save(str(path))

    raw = path.read_bytes()
    assert raw != b""
    assert b"Test" not in raw
    assert b"AAAAA" not in raw


def test_vault_backup_created(tmp_path: Path) -> None:
    """Zapis vaulta tworzy backup poprzedniej wersji."""
    path = tmp_path / "vault.bin"
    backup = tmp_path / "vault.backup.bin"

    vault = Vault()
    vault.add_entry("A", "111")
    vault.save(str(path))

    vault.add_entry("B", "222")
    vault.save(str(path))

    assert backup.exists()
    assert backup.read_bytes() != b""


def test_vault_tampering_detection(tmp_path: Path) -> None:
    """Zmiana danych w pliku powinna uniemożliwić odszyfrowanie."""
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("X", "12345")
    vault.save(str(path))

    raw = bytearray(path.read_bytes())
    raw[10] ^= 0xFF  # celowa korupcja
    path.write_bytes(raw)

    with pytest.raises(Exception):
        Vault.load(str(path))


def test_serialize_deserialize_symmetry() -> None:
    """serialize() i deserialize() muszą być symetryczne."""
    data = {"A": "111", "B": "222"}
    blob = serialize(data)
    restored = deserialize(blob)
    assert restored == data


def test_multiple_entries(tmp_path: Path) -> None:
    """Vault powinien poprawnie obsługiwać wiele wpisów."""
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("GitHub", "AAA")
    vault.add_entry("Google", "BBB")
    vault.add_entry("AWS", "CCC")
    vault.save(str(path))

    loaded = Vault.load(str(path))
    assert loaded.get_entry("GitHub").secret == "AAA"
    assert loaded.get_entry("Google").secret == "BBB"
    assert loaded.get_entry("AWS").secret == "CCC"
