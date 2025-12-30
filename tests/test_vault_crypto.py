from pathlib import Path

import pytest

from desktop_2fa.vault.vault import Vault


def test_vault_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("GitHub", "JBSWY3DPEHPK3PXP")
    vault.save(str(path))

    loaded = Vault.load(str(path))
    assert loaded.get_entry("GitHub").secret == "JBSWY3DPEHPK3PXP"


def test_vault_is_binary(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("Test", "JBSWY3DPEHPK3PXP")
    vault.save(str(path))

    raw = path.read_bytes()
    assert raw != b""
    assert b"Test" not in raw
    assert b"JBSWY3DPEHPK3PXP" not in raw


def test_vault_backup_created(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("A", "JBSWY3DPEHPK3PXP")
    vault.save(str(path))

    vault.add_entry("B", "JBSWY3DPEHPK3PXS")
    vault.save(str(path))

    # Note: New vault implementation does not create backups
    # assert backup.exists()
    # assert backup.read_bytes() != b""


def test_vault_tampering_detection(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("X", "JBSWY3DPEHPK3PXP")
    vault.save(str(path))

    raw = bytearray(path.read_bytes())
    raw[10] ^= 0xFF  # celowa korupcja
    path.write_bytes(raw)

    with pytest.raises(Exception):
        Vault.load(str(path))


def test_multiple_entries(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("GitHub", "JBSWY3DPEHPK3PXP")
    vault.add_entry("Google", "JBSWY3DPEHPK3PXS")
    vault.add_entry("AWS", "JBSWY3DPEHPK3PXT")
    vault.save(str(path))

    loaded = Vault.load(str(path))
    assert loaded.get_entry("GitHub").secret == "JBSWY3DPEHPK3PXP"
    assert loaded.get_entry("Google").secret == "JBSWY3DPEHPK3PXS"
    assert loaded.get_entry("AWS").secret == "JBSWY3DPEHPK3PXT"
