from pathlib import Path

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
        TotpEntry(issuer="Test", account_name="Test", secret="JBSWY3DPEHPK3PXP", period=0)
