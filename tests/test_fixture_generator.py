"""Regeneration must leave the committed fixture set intact on failure."""

import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest


@pytest.fixture
def generator() -> ModuleType:
    path = Path(__file__).parent / "fixtures" / "vaults" / "generate.py"
    spec = importlib.util.spec_from_file_location("fixture_generator", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generator_refuses_existing_snapshot(
    generator: ModuleType, tmp_path: Path
) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    manifest = existing / "manifest.json"
    manifest.write_bytes(b"previous manifest")
    with pytest.raises(FileExistsError, match="new output directory"):
        generator.generate(existing)
    assert manifest.read_bytes() == b"previous manifest"
    assert list(tmp_path.iterdir()) == [existing]


def test_interrupted_generation_preserves_previous_snapshot(
    generator: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    previous = tmp_path / "previous"
    previous.mkdir()
    (previous / "vault.bin").write_bytes(b"previous vault")
    (previous / "manifest.json").write_bytes(b"previous manifest")
    output = tmp_path / "new"

    def interrupt(staged: Path) -> None:
        (staged / "vault.bin").write_bytes(b"partially generated vault")
        assert not output.exists()
        raise KeyboardInterrupt

    monkeypatch.setattr(generator, "produce", interrupt)
    with pytest.raises(KeyboardInterrupt):
        generator.generate(output)
    assert (previous / "vault.bin").read_bytes() == b"previous vault"
    assert (previous / "manifest.json").read_bytes() == b"previous manifest"
    assert list(tmp_path.iterdir()) == [previous]


def test_generator_publishes_complete_snapshot(
    generator: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "new"
    blob = b"synthetic fixture"
    cases = [{"file": "vault.bin", "sha256": hashlib.sha256(blob).hexdigest()}]

    def produce(staged: Path) -> None:
        (staged / "vault.bin").write_bytes(blob)
        (staged / "manifest.json").write_text(json.dumps(cases), encoding="utf-8")
        assert not output.exists()

    # Publication tests must also run in CI's shallow checkout, without fetching
    # historical Git objects or executing historical releases.
    monkeypatch.setattr(generator, "produce", produce)
    generator.generate(output)
    assert json.loads((output / "manifest.json").read_text(encoding="utf-8")) == cases
    assert {path.name for path in output.iterdir()} == {
        "manifest.json",
        *(case["file"] for case in cases),
    }
    assert list(tmp_path.iterdir()) == [output]
    for case in cases:
        path = output / case["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == case["sha256"]
