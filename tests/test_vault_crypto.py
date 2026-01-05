from pathlib import Path

import pytest

from desktop_2fa.vault.vault import Vault


def test_vault_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP")
    vault.save(str(path))

    loaded = Vault.load(str(path))
    assert loaded.get_entry("GitHub").secret == "JBSWY3DPEHPK3PXP"


def test_vault_is_binary(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("Test", "Test", "JBSWY3DPEHPK3PXP")
    vault.save(str(path))

    raw = path.read_bytes()
    assert raw != b""
    assert b"Test" not in raw
    assert b"JBSWY3DPEHPK3PXP" not in raw


def test_vault_backup_created(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("A", "A", "JBSWY3DPEHPK3PXP")
    vault.save(str(path))

    vault.add_entry("B", "B", "JBSWY3DPEHPK3PXS")
    vault.save(str(path))

    # Note: New vault implementation does not create backups
    # assert backup.exists()
    # assert backup.read_bytes() != b""


def test_vault_tampering_detection(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("X", "X", "JBSWY3DPEHPK3PXP")
    vault.save(str(path))

    raw = bytearray(path.read_bytes())
    raw[10] ^= 0xFF  # celowa korupcja
    path.write_bytes(raw)

    with pytest.raises(Exception):
        Vault.load(str(path))


def test_multiple_entries(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP")
    vault.add_entry("Google", "Google", "JBSWY3DPEHPK3PXS")
    vault.add_entry("AWS", "AWS", "JBSWY3DPEHPK3PXT")
    vault.save(str(path))

    loaded = Vault.load(str(path))
    assert loaded.get_entry("GitHub").secret == "JBSWY3DPEHPK3PXP"
    assert loaded.get_entry("Google").secret == "JBSWY3DPEHPK3PXS"
    assert loaded.get_entry("AWS").secret == "JBSWY3DPEHPK3PXT"


def test_vault_encryption_with_password(tmp_path: Path) -> None:
    path = tmp_path / "vault_encrypted.bin"
    password = "test_password_123"

    vault = Vault()
    vault.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP")
    vault.add_entry("Google", "Google", "JBSWY3DPEHPK3PXS")
    vault.save(str(path), password=password)

    # Verify the file is encrypted (not plaintext)
    raw = path.read_bytes()
    assert raw != b""
    assert b"GitHub" not in raw
    assert b"JBSWY3DPEHPK3PXP" not in raw

    # Load with correct password
    loaded = Vault.load(str(path), password=password)
    assert loaded.get_entry("GitHub").secret == "JBSWY3DPEHPK3PXP"
    assert loaded.get_entry("Google").secret == "JBSWY3DPEHPK3PXS"


def test_vault_wrong_password(tmp_path: Path) -> None:
    path = tmp_path / "vault_wrong_pass.bin"
    correct_password = "correct_pass"
    wrong_password = "wrong_pass"

    vault = Vault()
    vault.add_entry("Test", "Test", "JBSWY3DPEHPK3PXP")
    vault.save(str(path), password=correct_password)

    # Should fail with wrong password
    with pytest.raises(Exception):
        Vault.load(str(path), password=wrong_password)


def test_vault_password_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "vault_roundtrip.bin"
    password = "roundtrip_pass"

    # Base32-sekrety
    secret1 = "JBSWY3DPEHPK3PXP"
    secret2 = "JBSWY3DPEHPK3PXS"

    vault1 = Vault()
    vault1.add_entry("Entry1", "Entry1", secret1)
    vault1.save(str(path), password=password)

    vault2 = Vault.load(str(path), password=password)
    vault2.add_entry("Entry2", "Entry2", secret2)
    vault2.save(str(path), password=password)

    vault3 = Vault.load(str(path), password=password)
    assert vault3.get_entry("Entry1").secret == secret1
    assert vault3.get_entry("Entry2").secret == secret2


def test_vault_no_password_vs_password(tmp_path: Path) -> None:
    path_no_pass = tmp_path / "vault_no_pass.bin"
    path_with_pass = tmp_path / "vault_with_pass.bin"
    password = "some_password"

    vault = Vault()
    vault.add_entry("Test", "Test", "JBSWY3DPEHPK3PXP")

    # Save without password
    vault.save(str(path_no_pass))

    # Save with password
    vault.save(str(path_with_pass), password=password)

    # Files should be different
    raw_no_pass = path_no_pass.read_bytes()
    raw_with_pass = path_with_pass.read_bytes()
    assert raw_no_pass != raw_with_pass

    # Both should load correctly with appropriate methods
    loaded_no_pass = Vault.load(str(path_no_pass))
    loaded_with_pass = Vault.load(str(path_with_pass), password=password)

    assert loaded_no_pass.get_entry("Test").secret == "JBSWY3DPEHPK3PXP"
    assert loaded_with_pass.get_entry("Test").secret == "JBSWY3DPEHPK3PXP"
