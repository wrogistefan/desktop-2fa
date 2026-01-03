from pathlib import Path
from typing import Any

import pytest

from desktop_2fa.vault import Vault
from desktop_2fa.vault.models import TotpEntry


def test_vault_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("GitHub", "JBSWY3DPEHPK3PXP")
    vault.save(str(path))

    loaded = Vault.load(str(path))
    entry = loaded.get_entry("GitHub")
    assert entry.secret == "JBSWY3DPEHPK3PXP"


def test_vault_file_is_binary(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("Test", "JBSWY3DPEHPK3PXP")
    vault.save(str(path))

    raw = path.read_bytes()
    assert raw != b""
    # upewniamy się, że jawne dane nie występują w pliku
    assert b"Test" not in raw
    assert b"JBSWY3DPEHPK3PXP" not in raw


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


def test_totp_entry_invalid_secret() -> None:
    with pytest.raises(ValueError, match="Invalid Base32 TOTP secret"):
        TotpEntry(issuer="Test", account_name="Test", secret="INVALID")


def test_totp_entry_invalid_period() -> None:
    with pytest.raises(ValueError, match="TOTP period must be positive"):
        TotpEntry(
            issuer="Test", account_name="Test", secret="JBSWY3DPEHPK3PXP", period=0
        )


def test_vault_load_invalid_magic_header(tmp_path: Path) -> None:
    """Test loading vault with invalid magic header."""
    path = tmp_path / "vault.bin"

    # Create a file with invalid magic header
    invalid_data = b"WRNG" + b"\x01" + b"16byte_salt_here" + b"encrypted_data"
    path.write_bytes(invalid_data)

    with pytest.raises(
        Exception, match="Invalid vault file format: incorrect magic header"
    ):
        Vault.load(str(path))


def test_vault_load_unsupported_version(tmp_path: Path) -> None:
    """Test loading vault with unsupported version."""
    path = tmp_path / "vault.bin"

    # Create a file with unsupported version
    invalid_data = b"D2FA" + b"\x02" + b"16byte_salt_here" + b"encrypted_data"
    path.write_bytes(invalid_data)

    with pytest.raises(Exception, match="Unsupported vault file version"):
        Vault.load(str(path))


def test_vault_load_empty_encrypted_blob(tmp_path: Path) -> None:
    """Test loading vault with empty encrypted blob."""
    path = tmp_path / "vault.bin"

    # Create a file with empty encrypted blob
    invalid_data = b"D2FA" + b"\x01" + b"16byte_salt_here"
    path.write_bytes(invalid_data)

    with pytest.raises(Exception, match="Vault file is invalid: empty encrypted blob"):
        Vault.load(str(path))


def test_vault_load_corrupted_json_data(tmp_path: Path) -> None:
    """Test loading vault with corrupted JSON data."""
    path = tmp_path / "vault.bin"

    # Create a valid vault structure but with corrupted JSON
    from desktop_2fa.crypto.aesgcm import encrypt
    from desktop_2fa.crypto.argon2 import derive_key

    password = "test_password"
    salt = b"16byte_salt_here"
    key = derive_key(password, salt)

    # Corrupted JSON data
    corrupted_json = b'{"invalid": json}'
    encrypted = encrypt(key, corrupted_json)

    valid_data = b"D2FA" + b"\x01" + salt + encrypted
    path.write_bytes(valid_data)

    with pytest.raises(Exception, match="Invalid password or corrupted vault"):
        Vault.load(str(path))


def test_vault_save_io_error(tmp_path: Path, monkeypatch: Any) -> None:
    """Test saving vault with IO error."""
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("Test", "JBSWY3DPEHPK3PXP")

    # Mock os.open to raise an exception
    def mock_open(*args: Any, **kwargs: Any) -> None:
        raise OSError("Permission denied")

    monkeypatch.setattr("os.open", mock_open)

    with pytest.raises(Exception, match="Failed to save vault: Permission denied"):
        vault.save(str(path))


def test_vault_save_cleanup_on_error(tmp_path: Path, monkeypatch: Any) -> None:
    """Test that temporary file is cleaned up when save fails."""
    path = tmp_path / "vault.bin"
    temp_path = path.with_suffix(".tmp")

    vault = Vault()
    vault.add_entry("Test", "JBSWY3DPEHPK3PXP")

    # Mock os.open to succeed but os.fdopen to fail
    def mock_open(*args: Any, **kwargs: Any) -> int:
        return 1  # fake file descriptor

    def mock_fdopen(*args: Any, **kwargs: Any) -> None:
        raise OSError("Write error")

    monkeypatch.setattr("os.open", mock_open)
    monkeypatch.setattr("os.fdopen", mock_fdopen)

    with pytest.raises(Exception, match="Failed to save vault: Write error"):
        vault.save(str(path))

    # Temporary file should be cleaned up
    assert not temp_path.exists()


def test_vault_load_malformed_json_edge_cases(tmp_path: Path) -> None:
    """Test loading vault with malformed JSON edge cases."""
    path = tmp_path / "vault.bin"

    # Create a valid vault structure but with malformed JSON that passes basic validation
    from desktop_2fa.crypto.aesgcm import encrypt
    from desktop_2fa.crypto.argon2 import derive_key

    password = "test_password"
    salt = b"16byte_salt_here"
    key = derive_key(password, salt)

    # JSON that's valid but has invalid structure for VaultData
    malformed_json = b'{"version": "invalid_type"}'
    encrypted = encrypt(key, malformed_json)

    valid_data = b"D2FA" + b"\x01" + salt + encrypted
    path.write_bytes(valid_data)

    with pytest.raises(Exception, match="Vault contains invalid data"):
        Vault.load(str(path), password="test_password")


def test_vault_save_os_level_errors(tmp_path: Path, monkeypatch: Any) -> None:
    """Test saving vault with OS-level file errors."""
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("Test", "JBSWY3DPEHPK3PXP")

    # Mock os.open to raise a specific OS error
    def mock_open(*args: Any, **kwargs: Any) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr("os.open", mock_open)

    with pytest.raises(
        Exception, match="Failed to save vault: No space left on device"
    ):
        vault.save(str(path))


def test_vault_save_cleanup_on_os_error(tmp_path: Path, monkeypatch: Any) -> None:
    """Test that temporary file is cleaned up when OS-level save fails."""
    path = tmp_path / "vault.bin"
    temp_path = path.with_suffix(".tmp")

    vault = Vault()
    vault.add_entry("Test", "JBSWY3DPEHPK3PXP")

    # Mock os.open to succeed but os.fsync to fail with OS error
    def mock_open(*args: Any, **kwargs: Any) -> int:
        return 1  # fake file descriptor

    def mock_fsync(fd: int) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr("os.open", mock_open)
    monkeypatch.setattr("os.fsync", mock_fsync)

    with pytest.raises(Exception, match="Failed to save vault:"):
        vault.save(str(path))

    # Temporary file should be cleaned up
    assert not temp_path.exists()


def test_vault_load_json_validation_edge_cases(tmp_path: Path) -> None:
    """Test loading vault with JSON that passes validation but fails model validation."""
    path = tmp_path / "vault.bin"

    # Create a valid vault structure but with JSON that has invalid field types
    from desktop_2fa.crypto.aesgcm import encrypt
    from desktop_2fa.crypto.argon2 import derive_key

    password = "test_password"
    salt = b"16byte_salt_here"
    key = derive_key(password, salt)

    # JSON with invalid field types that will fail Pydantic validation
    invalid_json = b'{"entries": [{"issuer": 123, "account_name": "test", "secret": "JBSWY3DPEHPK3PXP"}]}'
    encrypted = encrypt(key, invalid_json)

    valid_data = b"D2FA" + b"\x01" + salt + encrypted
    path.write_bytes(valid_data)

    with pytest.raises(Exception, match="Vault contains invalid data"):
        Vault.load(str(path), password="test_password")


def test_vault_load_no_password_default(tmp_path: Path) -> None:
    """Test loading vault with no password (uses default empty string)."""
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("Test", "JBSWY3DPEHPK3PXP")
    vault.save(str(path), password=None)  # Save with no password

    # Load with no password (should use default empty string)
    loaded = Vault.load(str(path), password=None)
    entry = loaded.get_entry("Test")
    assert entry.secret == "JBSWY3DPEHPK3PXP"


def test_vault_save_no_password_default(tmp_path: Path) -> None:
    """Test saving vault with no password (uses default empty string)."""
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("Test", "JBSWY3DPEHPK3PXP")

    # Save with no password (should use default empty string)
    vault.save(str(path), password=None)

    # File should be created
    assert path.exists()

    # Should be able to load with no password
    loaded = Vault.load(str(path), password=None)
    entry = loaded.get_entry("Test")
    assert entry.secret == "JBSWY3DPEHPK3PXP"


def test_vault_load_file_not_found(tmp_path: Path) -> None:
    """Test loading vault from non-existent file."""
    path = tmp_path / "nonexistent.bin"

    with pytest.raises(Exception, match="Failed to read vault file"):
        Vault.load(str(path))


def test_vault_load_file_too_short(tmp_path: Path) -> None:
    """Test loading vault file that is too short."""
    path = tmp_path / "vault.bin"

    # Create a file that's too short
    short_data = b"D2FA\x01"
    path.write_bytes(short_data)

    with pytest.raises(Exception, match="Vault file is too short or invalid format"):
        Vault.load(str(path))
