"""Fail closed for mismatched release tags and incomplete validation graphs."""

import json
import os
import sys
import tomllib
from pathlib import Path


def validate_tag(version: str, ref_type: str, ref_name: str) -> None:
    if ref_type == "tag" and ref_name != f"v{version}":
        raise ValueError("Release tag must exactly match v<project version>.")


def validate_gate(needs: dict[str, dict[str, str]]) -> None:
    required = {"quality", "tests", "package"}
    if set(needs) != required or any(
        needs[name].get("result") != "success" for name in required
    ):
        raise ValueError(
            "Quality, Tests and Package must all succeed; skips fail the gate."
        )


def main() -> None:
    if sys.argv[1:] == ["version"]:
        root = Path(__file__).resolve().parents[1]
        with (root / "pyproject.toml").open("rb") as stream:
            version = tomllib.load(stream)["project"]["version"]
        validate_tag(
            version, os.getenv("GITHUB_REF_TYPE", ""), os.getenv("GITHUB_REF_NAME", "")
        )
    elif sys.argv[1:] == ["gate"]:
        validate_gate(json.loads(os.environ["NEEDS_JSON"]))
    else:
        raise ValueError("Usage: release_checks.py version|gate")


if __name__ == "__main__":
    main()
