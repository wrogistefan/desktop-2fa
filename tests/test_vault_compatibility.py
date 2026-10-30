"""Immutable historical files exercise the public load/save contract."""

import base64
import hashlib
import json
from pathlib import Path

import pytest
from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from typer.testing import CliRunner

from desktop_2fa.cli.main import app
from desktop_2fa.crypto.argon2 import derive_key
from desktop_2fa.totp.generator import generate
from desktop_2fa.vault.vault import InvalidPassword, UnsupportedFormat, Vault

FIXTURES = Path(__file__).parent / "fixtures" / "vaults"
CASES = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
SUPPORTED = [case for case in CASES if case["supported"]]


def test_literal_argon2id_utf8_reference() -> None:
    assert (
        derive_key("synthetic-żółw-compatibility-only", bytes(range(16))).hex()
        == "ee2a246abcd0dd988b07c5077a127f85f3f9d761585dd15d3a5126499cc9d418"
    )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["file"])
def test_historical_fixture_integrity(case: dict) -> None:
    assert (
        hashlib.sha256((FIXTURES / case["file"]).read_bytes()).hexdigest()
        == case["sha256"]
    )


@pytest.mark.parametrize("case", SUPPORTED, ids=lambda case: case["file"])
def test_historical_load_and_resave(case: dict, tmp_path: Path) -> None:
    vault = Vault.load(FIXTURES / case["file"], case["password"])
    assert vault.data.model_dump() == case["expected"]
    path = tmp_path / "resaved.bin"
    vault.save(path, case["password"])
    loaded = Vault.load(path, case["password"])
    assert loaded.data.model_dump() == case["expected"]
    for entry, expected in zip(
        loaded.entries, case["expected"]["entries"], strict=True
    ):
        assert base64.b32decode(entry.secret, casefold=True) == base64.b32decode(
            expected["secret"]
        )
        for timestamp in (entry.period - 1, entry.period, entry.period + 1):
            assert generate(
                entry.secret,
                timestamp=timestamp,
                digits=entry.digits,
                period=entry.period,
                algorithm=entry.algorithm,
            ) == generate(
                expected["secret"],
                timestamp=timestamp,
                digits=expected["digits"],
                period=expected["period"],
                algorithm=expected["algorithm"],
            )
    # Missing names remain None; load has no implicit issuer-to-name migration.
    assert loaded.entries[2].account_name is None


@pytest.mark.parametrize("case", SUPPORTED, ids=lambda case: case["file"])
def test_saved_wire_contract(case: dict, tmp_path: Path) -> None:
    vault = Vault.load(FIXTURES / case["file"], case["password"])
    path = tmp_path / "wire.bin"
    vault.save(path, case["password"])
    blob = path.read_bytes()
    assert blob[:5] == b"D2FA\x01"
    # Independent decoder + literal KDF result above pin the writer
    # as well as the reader (writer/reader round trips alone can hide drift).
    key = hash_secret_raw(
        case["password"].encode("utf-8"),
        blob[5:21],
        time_cost=4,
        memory_cost=131072,
        parallelism=2,
        hash_len=32,
        type=Type.ID,
        version=19,
    )
    raw = AESGCM(key).decrypt(blob[21:33], blob[33:], None)
    assert json.loads(raw) == case["expected"]


@pytest.mark.parametrize("case", SUPPORTED, ids=lambda case: case["file"])
def test_historical_wrong_password(case: dict) -> None:
    with pytest.raises(InvalidPassword):
        Vault.load(FIXTURES / case["file"], "wrong-synthetic-password")


@pytest.mark.parametrize("offset", [33, -1], ids=["ciphertext", "tag"])
@pytest.mark.parametrize("case", SUPPORTED, ids=lambda case: case["file"])
def test_historical_authenticated_payload_tampering(
    case: dict, offset: int, tmp_path: Path
) -> None:
    blob = bytearray((FIXTURES / case["file"]).read_bytes())
    blob[offset] ^= 1
    path = tmp_path / "tampered.bin"
    path.write_bytes(blob)
    with pytest.raises(InvalidPassword):
        Vault.load(path, case["password"])


def test_pre_header_vault_is_unsupported() -> None:
    case = CASES[0]
    with pytest.raises(UnsupportedFormat, match="magic header"):
        Vault.load(FIXTURES / case["file"], case["password"])


def test_historical_empty_password_is_unsupported() -> None:
    path = FIXTURES / "v0.8.3-empty-password.bin"
    with pytest.raises(ValueError, match="empty"):
        Vault.load(path, "")
    with pytest.raises(InvalidPassword):
        Vault.load(path, "nonempty-synthetic-password")


def test_explicit_backup_restores_historical_entries(tmp_path: Path) -> None:
    case = SUPPORTED[0]
    path = tmp_path / "selected-vault"
    path.write_bytes((FIXTURES / case["file"]).read_bytes())
    original = path.read_bytes()
    result = CliRunner().invoke(
        app, ["--vault", str(path), "--password", case["password"], "backup"]
    )
    assert result.exit_code == 0, result.output
    backup = path.with_suffix(".backup.bin")
    assert Vault.load(backup, case["password"]).data.model_dump() == case["expected"]
    assert path.read_bytes() == original
    # A later normal save changes only the selected vault, preserving the backup.
    backup_bytes = backup.read_bytes()
    vault = Vault.load(path, case["password"])
    vault.entries.pop()
    vault.save(path, case["password"])
    assert len(Vault.load(path, case["password"]).entries) == 2
    assert backup.read_bytes() == backup_bytes
    assert Vault.load(backup, case["password"]).data.model_dump() == case["expected"]
