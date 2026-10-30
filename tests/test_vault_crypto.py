from pathlib import Path

import pytest

from desktop_2fa.vault.vault import InvalidPassword, Vault

TEST_PASSWORD = "test-vault-password"


def test_vault_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP")
    vault.save(str(path), TEST_PASSWORD)

    loaded = Vault.load(str(path), TEST_PASSWORD)
    assert loaded.get_entry("GitHub").secret == "JBSWY3DPEHPK3PXP"


def test_vault_is_binary(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("Test", "Test", "JBSWY3DPEHPK3PXP")
    vault.save(str(path), TEST_PASSWORD)

    raw = path.read_bytes()
    assert raw != b""
    assert b"Test" not in raw
    assert b"JBSWY3DPEHPK3PXP" not in raw


def test_normal_save_replaces_vault_without_implicit_backup(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("A", "A", "JBSWY3DPEHPK3PXP")
    vault.save(str(path), TEST_PASSWORD)

    vault.add_entry("B", "B", "JBSWY3DPEHPK3PXS")
    vault.save(str(path), TEST_PASSWORD)

    loaded = Vault.load(path, TEST_PASSWORD)
    assert [entry.account_name for entry in loaded.entries] == ["A", "B"]
    assert set(tmp_path.iterdir()) == {path, tmp_path / ".vault.bin.lock"}


def test_vault_tampering_detection(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("X", "X", "JBSWY3DPEHPK3PXP")
    vault.save(str(path), TEST_PASSWORD)

    raw = bytearray(path.read_bytes())
    raw[33] ^= 0xFF
    path.write_bytes(raw)

    with pytest.raises(InvalidPassword):
        Vault.load(str(path), TEST_PASSWORD)


def test_multiple_entries(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP")
    vault.add_entry("Google", "Google", "JBSWY3DPEHPK3PXS")
    vault.add_entry("AWS", "AWS", "JBSWY3DPEHPK3PXT")
    vault.save(str(path), TEST_PASSWORD)

    loaded = Vault.load(str(path), TEST_PASSWORD)
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
    with pytest.raises(InvalidPassword):
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
