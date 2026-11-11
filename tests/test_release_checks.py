"""Release validation must reject failed, skipped or incomplete evidence."""

from pathlib import Path

import pytest

from scripts.release_checks import validate_gate, validate_tag


@pytest.mark.parametrize("status", ["failure", "cancelled", "skipped", "pending", ""])
@pytest.mark.parametrize("job", ["quality", "tests", "package", "cli-minimum"])
def test_required_job_must_succeed(job: str, status: str) -> None:
    needs = {
        name: {"result": "success"}
        for name in ("quality", "tests", "package", "cli-minimum")
    }
    needs[job]["result"] = status
    with pytest.raises(ValueError):
        validate_gate(needs)


@pytest.mark.parametrize("missing", ["quality", "tests", "package", "cli-minimum"])
def test_missing_job_is_not_success(missing: str) -> None:
    needs = {
        name: {"result": "success"}
        for name in ("quality", "tests", "package", "cli-minimum")
    }
    del needs[missing]
    with pytest.raises(ValueError):
        validate_gate(needs)


def test_complete_graph_succeeds() -> None:
    validate_gate(
        {
            name: {"result": "success"}
            for name in ("quality", "tests", "package", "cli-minimum")
        }
    )


@pytest.mark.parametrize("tag", ["v0.8.3", "0.9.0", "v0.9.0-extra", "v0.9.00"])
def test_mismatched_tag_is_rejected(tag: str) -> None:
    with pytest.raises(ValueError):
        validate_tag("0.9.0", "tag", tag)


def test_matching_tag_and_ordinary_branch_are_accepted() -> None:
    validate_tag("0.9.0", "tag", "v0.9.0")
    validate_tag("0.9.0", "branch", "main")


def test_cli_boundary_versions_match_declared_floors() -> None:
    import tomllib

    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for package in ("typer", "click"):
        requirement = next(
            item
            for item in project["project"]["dependencies"]
            if item.startswith(package + ">=")
        )
        floor = requirement.split(">=", 1)[1]
        assert f"{package}=={floor}" in workflow
