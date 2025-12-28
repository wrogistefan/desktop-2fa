import base64
import hashlib
import hmac
import shutil
import struct
import tempfile
import time
from pathlib import Path
from typing import Any

import pytest

from desktop_2fa.cli import helpers


def generate(
    secret: str,
    timestamp: int | None = None,
    digits: int = 6,
    period: int = 30,
    algorithm: str = "SHA1",
) -> str:
    if timestamp is None:
        timestamp = int(time.time())

    counter = timestamp // period
    key = base64.b32decode(secret, casefold=True)

    if algorithm.upper() == "SHA1":
        digestmod = hashlib.sha1
    elif algorithm.upper() == "SHA256":
        digestmod = hashlib.sha256
    elif algorithm.upper() == "SHA512":
        digestmod = hashlib.sha512
    else:
        raise ValueError("Unsupported algorithm")

    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, digestmod).digest()
    offset = h[-1] & 0x0F
    code = (struct.unpack(">I", h[offset : offset + 4])[0] & 0x7FFFFFFF) % (10**digits)

    return str(code).zfill(digits)


@pytest.fixture
def fake_vault_env_helpers(tmp_path: Path, monkeypatch: Any) -> Path:
    """
    Przekierowuje get_vault_path() na katalog tymczasowy.
    Wszystkie operacje CLI działają na tymczasowym pliku.
    """
    fake_vault = tmp_path / "vault"

    monkeypatch.setattr(
        "desktop_2fa.cli.helpers.get_vault_path",
        lambda: str(fake_vault),
    )

    # Upewniamy się, że katalog jest czysty
    if fake_vault.parent.exists():
        shutil.rmtree(fake_vault.parent)
    fake_vault.parent.mkdir(parents=True, exist_ok=True)

    return fake_vault


def test_helpers_add_and_list_entries(fake_vault_env_helpers: Path) -> None:
    helpers.add_entry("GitHub", "JBSWY3DPEHPK3PXP")

    helpers.list_entries()  # to cover the print

    vault = helpers.load_vault()
    assert len(vault.entries) == 1
    assert vault.entries[0].issuer == "GitHub"
    assert vault.entries[0].name == "GitHub"


def test_helpers_generate_code(fake_vault_env_helpers: Path) -> None:
    helpers.add_entry("GitHub", "JBSWY3DPEHPK3PXP")

    # Should not raise
    helpers.generate_code("GitHub")


def test_helpers_remove_entry(fake_vault_env_helpers: Path) -> None:
    helpers.add_entry("GitHub", "JBSWY3DPEHPK3PXP")
    helpers.remove_entry("GitHub")

    vault = helpers.load_vault()
    assert len(vault.entries) == 0


def test_helpers_rename_entry(fake_vault_env_helpers: Path) -> None:
    helpers.add_entry("GitHub", "JBSWY3DPEHPK3PXP")
    helpers.rename_entry("GitHub", "GitHub2")

    vault = helpers.load_vault()
    assert vault.entries[0].issuer == "GitHub2"
    assert vault.entries[0].name == "GitHub2"


def test_helpers_export_and_import(
    fake_vault_env_helpers: Path, tmp_path: Path
) -> None:
    helpers.add_entry("GitHub", "JBSWY3DPEHPK3PXP")

    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp_path_file = Path(tmp.name)
    tmp.close()

    helpers.export_vault(str(tmp_path_file))

    # Reset vault
    vault = helpers.load_vault()
    vault.data.entries = []
    helpers.save_vault(vault)

    helpers.import_vault(str(tmp_path_file))
    vault = helpers.load_vault()

    assert len(vault.entries) == 1
    assert vault.entries[0].issuer == "GitHub"


def test_helpers_backup(fake_vault_env_helpers: Path) -> None:
    helpers.add_entry("GitHub", "JBSWY3DPEHPK3PXP")

    vault_path = Path(helpers.get_vault_path())
    backup_path = vault_path.with_suffix(".backup.bin")

    helpers.backup_vault()

    assert backup_path.exists()
    assert backup_path.stat().st_size > 0


def test_helpers_timestamp() -> None:
    ts = helpers.timestamp()
    assert isinstance(ts, str)
    assert ts.isdigit()


def test_helpers_export_vault_missing(
    fake_vault_env_helpers: Path, tmp_path: Path
) -> None:
    # Don't add entry, so vault file doesn't exist
    export_path = tmp_path / "export.bin"
    helpers.export_vault(str(export_path))
    # Should print "Vault does not exist."


def test_helpers_import_vault_missing(
    fake_vault_env_helpers: Path, tmp_path: Path
) -> None:
    missing = tmp_path / "nope.bin"
    helpers.import_vault(str(missing))
    # Should print "Source file does not exist."


def test_helpers_backup_vault_missing(fake_vault_env_helpers: Path) -> None:
    # Remove the vault file
    import os

    vault_path = helpers.get_vault_path()
    if os.path.exists(vault_path):
        os.remove(vault_path)
    helpers.backup_vault()
    # Should print "Vault does not exist."
