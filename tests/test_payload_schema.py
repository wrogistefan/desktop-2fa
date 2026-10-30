"""Unknown payload schemas and metadata must never be rewritten lossily."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from desktop_2fa.cli.main import app
from desktop_2fa.crypto.aesgcm import encrypt
from desktop_2fa.crypto.argon2 import derive_key
from desktop_2fa.vault import Vault, VaultData, VaultValidationError
from desktop_2fa.vault.vault import CorruptedVault, UnsupportedFormat

PASSWORD = "synthetic-payload-password"
ENTRY = {
    "secret": "JBSWY3DPEHPK3PXP",
    "issuer": "synthetic",
    "account_name": "account",
    "algorithm": "SHA256",
    "digits": 8,
    "period": 45,
}


def write_payload(path: Path, payload: dict) -> bytes:
    # Synthetic authenticated input, not a regenerated historical fixture.
    salt = bytes(range(16))
    encrypted = encrypt(derive_key(PASSWORD, salt), json.dumps(payload).encode("utf-8"))
    blob = b"D2FA\x01" + salt + encrypted
    path.write_bytes(blob)
    return blob


@pytest.mark.parametrize("version", [0, -1, 2, 999])
def test_unknown_payload_version_is_unsupported(tmp_path: Path, version: int) -> None:
    path = tmp_path / "vault.bin"
    before = write_payload(path, {"version": version, "entries": [ENTRY]})
    with pytest.raises(UnsupportedFormat, match="payload version"):
        Vault.load(path, PASSWORD)
    assert path.read_bytes() == before


@pytest.mark.parametrize("version", [True, 1.0, "1", None])
def test_version_is_not_coerced(tmp_path: Path, version: object) -> None:
    path = tmp_path / "vault.bin"
    before = write_payload(path, {"version": version, "entries": [ENTRY]})
    with pytest.raises(CorruptedVault):
        Vault.load(path, PASSWORD)
    assert path.read_bytes() == before


@pytest.mark.parametrize("level", ["vault", "entry"])
def test_unknown_metadata_is_refused_before_loss(tmp_path: Path, level: str) -> None:
    path = tmp_path / "vault.bin"
    payload = {"version": 1, "entries": [dict(ENTRY)]}
    target = payload if level == "vault" else payload["entries"][0]
    target["synthetic_extension"] = {"nested": ["synthetic-private-metadata", 42]}
    before = write_payload(path, payload)
    with pytest.raises(CorruptedVault) as error:
        Vault.load(path, PASSWORD)
    assert error.value.__suppress_context__
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "missing",
    [[], ["version"], ["issuer", "account_name"], ["algorithm", "digits", "period"]],
)
def test_supported_defaults_and_values_roundtrip(
    tmp_path: Path, missing: list[str]
) -> None:
    entry = {key: value for key, value in ENTRY.items() if key not in missing}
    payload = {"entries": [entry]}
    if "version" not in missing:
        payload["version"] = 1
    path = tmp_path / "vault.bin"
    write_payload(path, payload)
    vault = Vault.load(path, PASSWORD)
    expected = VaultData.model_validate(payload)
    assert vault.data == expected
    vault.save(path, PASSWORD)
    assert Vault.load(path, PASSWORD).data == expected
    assert vault.entries[0].secret == ENTRY["secret"]


def test_save_rejects_mutated_payload_version_before_io(tmp_path: Path) -> None:
    path = tmp_path / "vault.bin"
    vault = Vault()
    vault.save(path, PASSWORD)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    vault.data.version = 999
    with pytest.raises(VaultValidationError):
        vault.save(path, PASSWORD)
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


@pytest.mark.parametrize(
    "command",
    [
        ["add", "new", "synthetic", ENTRY["secret"]],
        ["rename", "account", "new"],
        ["export", "export.bin"],
    ],
)
@pytest.mark.parametrize("invalid", ["version", "metadata"])
def test_cli_cannot_rewrite_unsupported_payload(
    tmp_path: Path, command: list[str], invalid: str
) -> None:
    path = tmp_path / "vault.bin"
    payload = {"version": 999 if invalid == "version" else 1, "entries": [ENTRY]}
    if invalid == "metadata":
        payload["synthetic_extension"] = "synthetic-private-metadata"
    before = write_payload(path, payload)
    result = CliRunner().invoke(
        app,
        ["--vault", str(path), "--password", PASSWORD]
        + [str(tmp_path / arg) if arg == "export.bin" else arg for arg in command],
    )
    assert result.exit_code == 1, result.output
    assert "synthetic-private-metadata" not in result.output
    assert ENTRY["secret"] not in result.output
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]


def test_models_refuse_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        VaultData.model_validate({"entries": [ENTRY], "unknown": True})
    with pytest.raises(ValidationError):
        VaultData.model_validate({"entries": [{**ENTRY, "unknown": True}]})
