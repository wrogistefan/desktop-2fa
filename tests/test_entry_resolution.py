"""Name/issuer collisions must never select the first matching account."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from desktop_2fa.cli import helpers
from desktop_2fa.cli.main import app
from desktop_2fa.vault import AmbiguousEntry, TotpEntry, Vault, VaultData

PASSWORD = "synthetic-resolution-password"
RFC_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"


def entry(name: str | None, issuer: str | None) -> TotpEntry:
    return TotpEntry(account_name=name, issuer=issuer, secret=RFC_SECRET, digits=8)


@pytest.mark.parametrize("reverse", [False, True])
def test_account_name_precedes_issuer(reverse: bool) -> None:
    shadow = entry("first", "target")
    target = entry("target", "other")
    entries = [shadow, target]
    vault = Vault(VaultData(entries=entries[::-1] if reverse else entries))
    assert vault.get_entry("target") is target
    vault.remove_entry("target")
    assert vault.entries == [shadow]


@pytest.mark.parametrize("name", [None, "", "other"])
def test_unique_issuer_fallback(name: str | None) -> None:
    target = entry(name, "target")
    vault = Vault(VaultData(entries=[target]))
    assert vault.get_entry("target") is target
    vault.remove_entry("target")
    assert vault.entries == []


def test_exact_name_wins_over_multiple_issuers() -> None:
    target = entry("target", None)
    vault = Vault(
        VaultData(entries=[entry("one", "target"), entry("two", "target"), target])
    )
    assert vault.get_entry("target") is target


@pytest.mark.parametrize(
    "entries",
    [
        [entry("target", "one"), entry("target", "two")],
        [entry(None, "target"), entry("", "target")],
    ],
)
@pytest.mark.parametrize("reverse", [False, True])
def test_ambiguous_resolution_rejects_without_mutation(
    entries: list[TotpEntry],
    reverse: bool,
) -> None:
    vault = Vault(VaultData(entries=entries[::-1] if reverse else entries))
    before = vault.data.model_dump()
    for operation in [vault.get_entry, vault.remove_entry]:
        with pytest.raises(AmbiguousEntry, match="Ambiguous entry"):
            operation("target")
        assert vault.data.model_dump() == before


@pytest.mark.parametrize("query", ["missing", "TARGET", "ISSUER"])
def test_lookup_is_case_sensitive_and_missing_is_rejected(query: str) -> None:
    vault = Vault(VaultData(entries=[entry("target", "issuer")]))
    with pytest.raises(ValueError, match="not found"):
        vault.get_entry(query)


@pytest.fixture
def collision_path(tmp_path: Path) -> Path:
    shadow = entry("first", "target")
    shadow.secret = "JBSWY3DPEHPK3PXP"
    vault = Vault(VaultData(entries=[shadow, entry("target", "other")]))
    path = tmp_path / "selected-vault"
    vault.save(path, PASSWORD)
    return path


@pytest.mark.parametrize("interface", ["cli", "helper"])
def test_generated_code_belongs_to_exact_account(
    collision_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    interface: str,
) -> None:
    monkeypatch.setattr("desktop_2fa.totp.generator.time.time", lambda: 59)
    if interface == "cli":
        result = CliRunner().invoke(
            app,
            [
                "--vault",
                str(collision_path),
                "--password",
                PASSWORD,
                "code",
                "target",
                "--raw",
            ],
        )
        assert result.exit_code == 0, result.output
        assert result.output.strip() == "94287082"
    else:
        helpers.generate_code(collision_path, "target", PASSWORD)
        assert capsys.readouterr().out.strip() == "94287082"


@pytest.mark.parametrize("interface", ["cli", "helper"])
def test_removal_changes_only_exact_account(
    collision_path: Path, interface: str
) -> None:
    if interface == "cli":
        result = CliRunner().invoke(
            app,
            [
                "--vault",
                str(collision_path),
                "--password",
                PASSWORD,
                "remove",
                "target",
            ],
        )
        assert result.exit_code == 0, result.output
    else:
        helpers.remove_entry(collision_path, "target", PASSWORD)
    loaded = Vault.load(collision_path, PASSWORD)
    assert [(item.account_name, item.issuer) for item in loaded.entries] == [
        ("first", "target")
    ]


@pytest.mark.parametrize("interface", ["cli", "helper"])
@pytest.mark.parametrize("operation", ["code", "remove"])
@pytest.mark.parametrize("duplicate_names", [False, True])
def test_ambiguity_preserves_saved_vault(
    tmp_path: Path,
    interface: str,
    operation: str,
    duplicate_names: bool,
) -> None:
    entries = (
        [entry("target", "one"), entry("target", "two")]
        if duplicate_names
        else [entry("one", "target"), entry(None, "target")]
    )
    path = tmp_path / "ambiguous-vault"
    Vault(VaultData(entries=entries)).save(path, PASSWORD)
    before = path.read_bytes()
    if interface == "cli":
        result = CliRunner().invoke(
            app, ["--vault", str(path), "--password", PASSWORD, operation, "target"]
        )
        assert result.exit_code == 6
        assert "Ambiguous entry" in result.output
        assert "Invalid vault password" not in result.output
    else:
        action = helpers.generate_code if operation == "code" else helpers.remove_entry
        with pytest.raises(AmbiguousEntry, match="Ambiguous entry"):
            action(path, "target", PASSWORD)
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "mode", ["--json", "--quiet", "--raw", "--copy", "--copy-only"]
)
def test_ambiguous_code_modes_do_not_generate_or_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    path = tmp_path / "shared-issuer"
    Vault(VaultData(entries=[entry("one", "target"), entry("two", "target")])).save(
        path, PASSWORD
    )
    before = path.read_bytes()

    def forbidden(*args: object, **kwargs: object) -> str:
        pytest.fail("Ambiguous lookup must stop before generation or clipboard access")

    monkeypatch.setattr("desktop_2fa.totp.generator.generate", forbidden)
    monkeypatch.setattr("desktop_2fa.cli.clipboard.copy_to_clipboard", forbidden)
    result = CliRunner().invoke(
        app, ["--vault", str(path), "--password", PASSWORD, "code", "target", mode]
    )
    assert result.exit_code == 6
    if mode == "--json":
        assert json.loads(result.output) == {
            "error": "entry_ambiguous",
            "message": "Ambiguous entry 'target': multiple entries match. Operation aborted.",
        }
    elif mode == "--quiet":
        assert result.output == ""
    else:
        assert "Ambiguous entry" in result.output
    assert path.read_bytes() == before


@pytest.mark.parametrize("interface", ["cli", "helper"])
def test_missing_removal_preserves_saved_vault(
    collision_path: Path, interface: str
) -> None:
    before = collision_path.read_bytes()
    if interface == "cli":
        result = CliRunner().invoke(
            app,
            [
                "--vault",
                str(collision_path),
                "--password",
                PASSWORD,
                "remove",
                "missing",
            ],
        )
        assert result.exit_code != 0
        assert result.exit_code == 3
        assert "not found" in result.output
    else:
        with pytest.raises(ValueError, match="not found"):
            helpers.remove_entry(collision_path, "missing", PASSWORD)
    assert collision_path.read_bytes() == before
