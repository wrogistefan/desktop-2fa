"""Release validation must reject failed, skipped or incomplete evidence."""

import pytest

from scripts.release_checks import validate_gate, validate_tag


@pytest.mark.parametrize("status", ["failure", "cancelled", "skipped", "pending", ""])
@pytest.mark.parametrize("job", ["quality", "tests", "package"])
def test_required_job_must_succeed(job: str, status: str) -> None:
    needs = {name: {"result": "success"} for name in ("quality", "tests", "package")}
    needs[job]["result"] = status
    with pytest.raises(ValueError):
        validate_gate(needs)


def test_missing_job_is_not_success() -> None:
    with pytest.raises(ValueError):
        validate_gate(
            {"quality": {"result": "success"}, "tests": {"result": "success"}}
        )


def test_complete_graph_succeeds() -> None:
    validate_gate(
        {name: {"result": "success"} for name in ("quality", "tests", "package")}
    )


@pytest.mark.parametrize("tag", ["v0.8.3", "0.9.0", "v0.9.0-extra", "v0.9.00"])
def test_mismatched_tag_is_rejected(tag: str) -> None:
    with pytest.raises(ValueError):
        validate_tag("0.9.0", "tag", tag)


def test_matching_tag_and_ordinary_branch_are_accepted() -> None:
    validate_tag("0.9.0", "tag", "v0.9.0")
    validate_tag("0.9.0", "branch", "main")
