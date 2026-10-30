"""Synthetic evaluator output must never cross the diagnostic boundary."""

from pathlib import Path
from typing import Any

import pytest
import typer
from click import Command

from desktop_2fa.cli import commands, helpers
from desktop_2fa.cli.output import OutputMode, output_mode

SYNTHETIC_SECRET = "synthetic-evaluator-private-value"


class SensitiveScore(int):
    def __str__(self) -> str:
        return SYNTHETIC_SECRET


def evaluator_result() -> dict[str, Any]:
    return {
        "score": SensitiveScore(0),
        "feedback": {
            "warning": SYNTHETIC_SECRET,
            "suggestions": [SYNTHETIC_SECRET],
        },
    }


@pytest.mark.parametrize("reject", [False, True])
def test_strength_enforcement_emits_only_fixed_text(
    reject: bool, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        helpers, "load_config", lambda: {"security": {"reject_weak_passwords": reject}}
    )
    monkeypatch.setattr(
        helpers, "evaluate_password_strength", lambda _: evaluator_result()
    )
    monkeypatch.setattr(typer, "confirm", lambda _: True)
    token = output_mode.set(OutputMode())
    try:
        if reject:
            with pytest.raises(typer.Exit) as caught:
                helpers._enforce_password_strength(SYNTHETIC_SECRET)
            assert caught.value.exit_code == 6
        else:
            helpers._enforce_password_strength(SYNTHETIC_SECRET)
    finally:
        output_mode.reset(token)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "Password too weak. Use a longer, less predictable password.\n"
    )


def test_unlock_emits_only_fixed_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(commands, "_path", lambda _: tmp_path / "synthetic-vault")
    monkeypatch.setattr(helpers, "ensure_existing_vault", lambda _: True)
    monkeypatch.setattr(
        helpers, "get_password_for_vault", lambda *a, **k: SYNTHETIC_SECRET
    )
    monkeypatch.setattr(helpers, "load_vault_or_print_error", lambda *a: object())
    monkeypatch.setattr(
        helpers,
        "load_config",
        lambda: {"security": {"warn_on_weak_existing_passwords": True}},
    )
    monkeypatch.setattr(
        commands, "evaluate_password_strength", lambda _: evaluator_result()
    )
    token = output_mode.set(OutputMode())
    try:
        commands.unlock_vault(typer.Context(Command("unlock")))
    finally:
        output_mode.reset(token)
    captured = capsys.readouterr()
    assert SYNTHETIC_SECRET not in captured.out + captured.err
    assert captured.err == (
        "Warning: Your vault password is weak. Consider changing it.\n"
    )
