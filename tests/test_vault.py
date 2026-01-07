from pathlib import Path
from typing import Any

import pytest

from desktop_2fa.vault import Vault
from desktop_2fa.vault.models import TotpEntry, VaultData


def test_vault_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP")
    vault.save(str(path))

    loaded = Vault.load(str(path))
    entry = loaded.get_entry("GitHub")
    assert entry.secret == "JBSWY3DPEHPK3PXP"


def test_vault_file_is_binary(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("Test", "Test", "JBSWY3DPEHPK3PXP")
    vault.save(str(path))

    raw = path.read_bytes()
    assert raw != b""
    # upewniamy się, że jawne dane nie występują w pliku
    assert b"Test" not in raw
    assert b"JBSWY3DPEHPK3PXP" not in raw


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


def test_totp_entry_invalid_secret() -> None:
    with pytest.raises(ValueError, match="Invalid Base32 TOTP secret"):
        TotpEntry(issuer="Test", account_name="Test", secret="INVALID")


def test_totp_entry_invalid_period() -> None:
    with pytest.raises(ValueError, match="TOTP period must be positive"):
        TotpEntry(
            issuer="Test", account_name="Test", secret="JBSWY3DPEHPK3PXP", period=0
        )


def test_vault_load_invalid_magic_header(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    # Create a file with invalid magic header
    invalid_data = b"WRNG" + b"\x01" + b"16byte_salt_here" + b"encrypted_data"
    path.write_bytes(invalid_data)

    with pytest.raises(
        Exception, match="Invalid vault file format: incorrect magic header"
    ):
        Vault.load(str(path))


def test_vault_load_unsupported_version(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    # Create a file with unsupported version
    invalid_data = b"D2FA" + b"\x02" + b"16byte_salt_here" + b"encrypted_data"
    path.write_bytes(invalid_data)

    with pytest.raises(Exception, match="Unsupported vault file version"):
        Vault.load(str(path))


def test_vault_load_empty_encrypted_blob(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    # Create a file with empty encrypted blob
    invalid_data = b"D2FA" + b"\x01" + b"16byte_salt_here"
    path.write_bytes(invalid_data)

    with pytest.raises(Exception, match="Vault file is invalid: empty encrypted blob"):
        Vault.load(str(path))


def test_vault_load_corrupted_json_data(tmp_path: Path) -> None:
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
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("Test", "Test", "JBSWY3DPEHPK3PXP")

    # Mock os.open to raise an exception
    def mock_open(*args: Any, **kwargs: Any) -> None:
        raise OSError("Permission denied")

    monkeypatch.setattr("os.open", mock_open)

    with pytest.raises(Exception, match="Failed to save vault: Permission denied"):
        vault.save(str(path))


def test_vault_save_cleanup_on_error(tmp_path: Path, monkeypatch: Any) -> None:
    path = tmp_path / "vault.bin"
    temp_path = path.with_suffix(".tmp")

    vault = Vault()
    vault.add_entry("Test", "Test", "JBSWY3DPEHPK3PXP")

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
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("Test", "Test", "JBSWY3DPEHPK3PXP")

    # Mock os.open to raise a specific OS error
    def mock_open(*args: Any, **kwargs: Any) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr("os.open", mock_open)

    with pytest.raises(
        Exception, match="Failed to save vault: No space left on device"
    ):
        vault.save(str(path))


def test_vault_save_cleanup_on_os_error(tmp_path: Path, monkeypatch: Any) -> None:
    path = tmp_path / "vault.bin"
    temp_path = path.with_suffix(".tmp")

    vault = Vault()
    vault.add_entry("Test", "Test", "JBSWY3DPEHPK3PXP")

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
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("Test", "Test", "JBSWY3DPEHPK3PXP")
    vault.save(str(path), password=None)  # Save with no password

    # Load with no password (should use default empty string)
    loaded = Vault.load(str(path), password=None)
    entry = loaded.get_entry("Test")
    assert entry.secret == "JBSWY3DPEHPK3PXP"


def test_vault_save_no_password_default(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("Test", "Test", "JBSWY3DPEHPK3PXP")

    # Save with no password (should use default empty string)
    vault.save(str(path), password=None)

    # File should be created
    assert path.exists()

    # Should be able to load with no password
    loaded = Vault.load(str(path), password=None)
    entry = loaded.get_entry("Test")
    assert entry.secret == "JBSWY3DPEHPK3PXP"


def test_vault_load_file_not_found(tmp_path: Path) -> None:
    path = tmp_path / "nonexistent.bin"

    with pytest.raises(Exception, match="Vault file not found"):
        Vault.load(str(path))


def test_vault_load_file_too_short(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    # Create a file that's too short
    short_data = b"D2FA\x01"
    path.write_bytes(short_data)

    with pytest.raises(Exception, match="Vault file is too short or invalid format"):
        Vault.load(str(path))


def test_vault_add_entry_duplicate_name() -> None:
    vault = Vault()
    vault.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP")

    with pytest.raises(ValueError, match='An entry with name "GitHub" already exists'):
        vault.add_entry("GitHub", "GitHub", "ABCDEFGHIJKL1234")


def test_vault_load_duplicate_names_warning(tmp_path: Path, capsys: Any) -> None:
    path = tmp_path / "vault.bin"

    # Create vault data with duplicate names manually
    data = VaultData(
        entries=[
            TotpEntry(
                account_name="GitHub", issuer="GitHub", secret="JBSWY3DPEHPK3PXP"
            ),
            TotpEntry(
                account_name="GitHub", issuer="GitHub", secret="JBSWY3DPEHPK3PXP"
            ),
        ]
    )
    vault = Vault(data)
    vault.save(str(path))

    # Load the vault - should show warning but succeed
    loaded = Vault.load(str(path))

    # Check that warning was printed
    captured = capsys.readouterr()
    assert (
        'Warning: Your vault contains multiple entries with the same name: "GitHub"'
        in captured.out
    )

    # Vault should still load successfully
    assert len(loaded.entries) == 2


def test_vault_rename_entry_not_implemented() -> None:
    vault = Vault()
    vault.add_entry("Test", "Test", "JBSWY3DPEHPK3PXP")

    with pytest.raises(NotImplementedError, match="rename will be implemented"):
        vault.rename_entry("Test", "NewName")


def test_vault_load_permission_error(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    # Create a mock that raises PermissionError
    import builtins

    original_open = builtins.open

    def mock_open(*args: Any, **kwargs: Any) -> None:
        raise PermissionError("Permission denied")

    builtins.open = mock_open  # type: ignore[assignment]
    try:
        with pytest.raises(Exception, match="Cannot access vault file"):
            Vault.load(str(path))
    finally:
        builtins.open = original_open


def test_vault_load_os_error(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    # Create a mock that raises OSError
    import builtins

    original_open = builtins.open

    def mock_open(*args: Any, **kwargs: Any) -> None:
        raise OSError("Disk error")

    builtins.open = mock_open  # type: ignore[assignment]
    try:
        with pytest.raises(Exception, match="Failed to read vault file"):
            Vault.load(str(path))
    finally:
        builtins.open = original_open


def test_vault_save_permission_error_cleanup(tmp_path: Path, monkeypatch: Any) -> None:
    from desktop_2fa.vault.vault import PermissionDenied

    path = tmp_path / "vault.bin"
    temp_path = path.with_suffix(".tmp")

    vault = Vault()
    vault.add_entry("Test", "Test", "JBSWY3DPEHPK3PXP")

    # Mock os.replace to raise PermissionError after temp file is written
    def mock_replace(src: Any, dst: Any) -> None:
        raise PermissionError("Permission denied")

    monkeypatch.setattr("os.replace", mock_replace)

    with pytest.raises(PermissionDenied):
        vault.save(str(path))

    # Temp file should be cleaned up
    assert not temp_path.exists()


def test_vault_save_os_error_cleanup(tmp_path: Path, monkeypatch: Any) -> None:
    from desktop_2fa.vault.vault import VaultIOError

    path = tmp_path / "vault.bin"
    temp_path = path.with_suffix(".tmp")

    vault = Vault()
    vault.add_entry("Test", "Test", "JBSWY3DPEHPK3PXP")

    # Mock os.open to return a fake fd, then fail on fdopen
    def mock_open(*args: Any, **kwargs: Any) -> int:
        return 1  # fake file descriptor

    def mock_fdopen(fd: int, mode: str = "w") -> Any:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr("os.open", mock_open)
    monkeypatch.setattr("os.fdopen", mock_fdopen)

    with pytest.raises(VaultIOError):
        vault.save(str(path))

    # Temp file should be cleaned up
    assert not temp_path.exists()


def test_vault_save_os_error_cleanup_on_unlink_failure(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from desktop_2fa.vault.vault import VaultIOError

    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("Test", "Test", "JBSWY3DPEHPK3PXP")

    # First mock os.open to succeed, then os.fsync to fail with OS error
    # Then mock unlink to also fail
    call_count = [0]

    def mock_open(*args: Any, **kwargs: Any) -> int:
        call_count[0] += 1
        return 1  # fake file descriptor

    def mock_fsync(fd: int) -> None:
        raise OSError(28, "No space left on device")

    # Make unlink fail with OSError (covers lines 278-281)
    def mock_unlink(path: Any) -> None:
        raise OSError("Cannot remove temp file")

    monkeypatch.setattr("os.open", mock_open)
    monkeypatch.setattr("os.fsync", mock_fsync)
    monkeypatch.setattr("pathlib.Path.unlink", mock_unlink)

    with pytest.raises(VaultIOError):
        vault.save(str(path))

    # The test passes if VaultIOError is raised (unlink failure doesn't propagate)


def test_vault_save_permission_error_cleanup_on_unlink_failure(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from desktop_2fa.vault.vault import PermissionDenied

    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("Test", "Test", "JBSWY3DPEHPK3PXP")

    # Mock os.replace to raise PermissionError
    # Then mock unlink to also fail with OSError (covers lines 273-274)
    def mock_replace(src: Any, dst: Any) -> None:
        raise PermissionError("Permission denied")

    # Make unlink fail with OSError
    def mock_unlink(path: Any) -> None:
        raise OSError("Cannot remove temp file")

    monkeypatch.setattr("os.replace", mock_replace)
    monkeypatch.setattr("pathlib.Path.unlink", mock_unlink)

    with pytest.raises(PermissionDenied):
        vault.save(str(path))

    # The test passes if PermissionDenied is raised (unlink failure doesn't propagate)
