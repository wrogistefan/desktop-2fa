from pathlib import Path

import pytest

from desktop_2fa.vault import Vault


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
    vault.add_entry("Test", "AAAAA")
    vault.save(str(path))

    raw = path.read_bytes()
    assert raw != b""
    # upewniamy się, że jawne dane nie występują w pliku
    assert b"Test" not in raw
    assert b"AAAAA" not in raw


def test_vault_tampering_detection(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"

    vault = Vault()
    vault.add_entry("X", "12345")
    vault.save(str(path))

    raw = bytearray(path.read_bytes())
    raw[10] ^= 0xFF  # celowa korupcja
    path.write_bytes(raw)

    with pytest.raises(Exception):
        Vault.load(str(path))
