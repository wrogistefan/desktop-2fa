"""Encrypted exports preserve source and destination on refusal or failed writes."""

import os
from pathlib import Path

import pytest
from rich.text import Text
from typer.testing import CliRunner

from desktop_2fa.cli import helpers
from desktop_2fa.cli.main import app
from desktop_2fa.vault import ExportRefused, Vault
from desktop_2fa.vault.vault import VaultIOError

PASSWORD = "synthetic-export-password"
SECRET = "JBSWY3DPEHPK3PXP"


@pytest.fixture
def source(tmp_path: Path) -> Path:
    path = tmp_path / "source.bin"
    vault = Vault()
    for algorithm, digits, period in [
        ("SHA1", 6, 30),
        ("SHA256", 7, 45),
        ("SHA512", 8, 60),
    ]:
        vault.add_entry(
            algorithm,
            "synthetic",
            SECRET,
            algorithm=algorithm,
            digits=digits,
            period=period,
        )
    vault.save(path, PASSWORD)
    return path


def invoke(source: Path, destination: Path, force: bool = False):
    return CliRunner().invoke(
        app,
        ["--vault", str(source), "--password", PASSWORD, "export", str(destination)]
        + (["--force"] if force else []),
    )


@pytest.mark.parametrize("existing", [None, "ordinary", "vault"])
@pytest.mark.parametrize("force", [False, True])
def test_export_destination_policy(
    source: Path, existing: str | None, force: bool
) -> None:
    destination = source.parent / "export.bin"
    original = source.read_bytes()
    if existing == "ordinary":
        destination.write_bytes(b"synthetic ordinary file")
    elif existing == "vault":
        Vault().save(destination, "synthetic-other-password")
    before = destination.read_bytes() if existing else None
    result = invoke(source, destination, force)
    assert source.read_bytes() == original
    if existing and not force:
        assert result.exit_code == 6, result.output
        assert "--force" in result.output
        assert destination.read_bytes() == before
        assert "Exported vault" not in result.output
    else:
        assert result.exit_code == 0, result.output
        assert destination.read_bytes().startswith(b"D2FA\x01")
        assert (
            Vault.load(destination, PASSWORD).data == Vault.load(source, PASSWORD).data
        )
    assert set(source.parent.iterdir()) == {source, destination}


@pytest.mark.parametrize(
    "alias", ["same", "relative", "hardlink", "symlink", "dangling"]
)
@pytest.mark.parametrize("force", [False, True])
def test_source_aliases_and_symlinks_are_refused(
    source: Path, alias: str, force: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = source.parent / "alias.bin"
    if alias == "same":
        destination = source
    elif alias == "relative":
        monkeypatch.chdir(source.parent)
        destination = Path(".") / source.name
    else:
        try:
            if alias == "hardlink":
                os.link(source, destination)
            else:
                destination.symlink_to(
                    source if alias == "symlink" else source.parent / "missing"
                )
        except OSError as error:
            pytest.skip(f"Filesystem cannot create {alias}: {error}")
    before = source.read_bytes()
    result = invoke(source, destination, force)
    assert result.exit_code == 6, result.output
    assert source.read_bytes() == before
    if alias in {"symlink", "dangling"}:
        assert destination.is_symlink()
    if alias == "dangling":
        assert not (source.parent / "missing").exists()
    else:
        assert destination.read_bytes() == before


@pytest.mark.parametrize("force", [False, True])
def test_helper_has_same_policy(source: Path, force: bool) -> None:
    destination = source.parent / "helper.bin"
    destination.write_bytes(b"synthetic previous output")
    if force:
        helpers.export_vault(source, destination, PASSWORD, force=True)
        assert (
            Vault.load(destination, PASSWORD).data == Vault.load(source, PASSWORD).data
        )
    else:
        with pytest.raises(ExportRefused):
            helpers.export_vault(source, destination, PASSWORD)
        assert destination.read_bytes() == b"synthetic previous output"
    before = source.read_bytes()
    with pytest.raises(ExportRefused):
        helpers.export_vault(source, source, PASSWORD, force=force)
    assert source.read_bytes() == before


def test_concurrent_creator_wins(source: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    destination = source.parent / "export.bin"
    before = source.read_bytes()
    real_link = os.link

    def racing_link(src, dst):
        Path(dst).write_bytes(b"synthetic competing writer")
        real_link(src, dst)

    monkeypatch.setattr("desktop_2fa.vault.vault.os.link", racing_link)
    result = invoke(source, destination)
    assert result.exit_code == 6, result.output
    assert destination.read_bytes() == b"synthetic competing writer"
    assert source.read_bytes() == before
    assert set(source.parent.iterdir()) == {source, destination}


@pytest.mark.parametrize(
    "operation,force",
    [("fsync", False), ("link", False), ("fsync", True), ("replace", True)],
)
def test_write_failure_preserves_bytes(
    source: Path, monkeypatch: pytest.MonkeyPatch, operation: str, force: bool
) -> None:
    destination = source.parent / "export.bin"
    if force:
        destination.write_bytes(b"synthetic previous output")
    before = {p: p.read_bytes() for p in source.parent.iterdir()}

    def fail(*args, **kwargs):
        raise OSError("synthetic write failure")

    monkeypatch.setattr(f"desktop_2fa.vault.vault.os.{operation}", fail)
    result = invoke(source, destination, force)
    assert result.exit_code == 1, result.output
    assert "Exported vault" not in result.output
    assert {p: p.read_bytes() for p in source.parent.iterdir()} == before


def test_save_create_only_preserves_existing_file(source: Path) -> None:
    before = source.read_bytes()
    with pytest.raises(ExportRefused):
        Vault().save(source, PASSWORD, overwrite=False)
    assert source.read_bytes() == before
    assert list(source.parent.iterdir()) == [source]


def test_save_create_only_link_failure_is_io_error(
    source: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args, **kwargs):
        raise OSError("synthetic unsupported hard links")

    monkeypatch.setattr("desktop_2fa.vault.vault.os.link", fail)
    with pytest.raises(VaultIOError):
        Vault().save(source.parent / "new.bin", PASSWORD, overwrite=False)
    assert list(source.parent.iterdir()) == [source]


@pytest.mark.parametrize("color", [False, True])
def test_help_describes_binary_export(color: bool) -> None:
    result = CliRunner().invoke(app, ["export", "--help"], color=color)
    assert result.exit_code == 0
    # Rich can put ANSI styling between the dashes and option name in CI.
    visible = Text.from_ansi(result.output).plain
    assert "D2FA" in visible
    assert "JSON" not in visible
    assert "--force" in visible
