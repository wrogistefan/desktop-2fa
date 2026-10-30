"""Controlled-clock UI regressions; no real vault or clipboard is accessed."""

import asyncio

import pytest
from textual.containers import Container
from textual.widgets import Label, ListView

from desktop_2fa.totp.generator import generate
from desktop_2fa.ui_textual.app import D2FAApp
from desktop_2fa.vault import Vault
from desktop_2fa.vault.models import TotpEntry, VaultData


def make_app(monkeypatch: pytest.MonkeyPatch, entries: list[TotpEntry]) -> D2FAApp:
    vault = Vault(VaultData(entries=entries))
    monkeypatch.setattr(Vault, "load", lambda *args: vault)
    return D2FAApp("synthetic-not-opened", "synthetic-password")


def test_active_timer_tolerates_removed_screen_children(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = make_app(
        monkeypatch, [TotpEntry(account_name="synthetic", secret="MY======")]
    )
    monkeypatch.setattr("desktop_2fa.ui_textual.app.time.time", lambda: 29)

    async def check() -> None:
        async with app.run_test() as pilot:
            await pilot.click("#generate")
            assert app._displayed_code is not None
            await app.query_one(Container).remove()
            await pilot.pause(0.35)
            assert app._displayed_code is None
            app._update_validity()

    asyncio.run(check())


@pytest.mark.parametrize("period", [30, 45, 60])
@pytest.mark.parametrize("action", ["generate", "copy"])
def test_validity_expires_and_copy_uses_current_code(
    monkeypatch: pytest.MonkeyPatch, period: int, action: str
) -> None:
    entry = TotpEntry(
        account_name="synthetic",
        secret="MZXQ====",
        algorithm="SHA512",
        digits=7,
        period=period,
    )
    before = entry.model_dump()
    app = make_app(monkeypatch, [entry])
    clock = [period - 1]
    monkeypatch.setattr("desktop_2fa.ui_textual.app.time.time", lambda: clock[0])
    copied: list[str] = []
    monkeypatch.setattr("pyperclip.copy", copied.append)

    def expected_code() -> str:
        return generate(
            entry.secret,
            timestamp=clock[0],
            algorithm=entry.algorithm,
            digits=entry.digits,
            period=period,
        )

    async def check() -> None:
        async with app.run_test() as pilot:
            await pilot.click(f"#{action}")
            output = app.query_one("#output", Label)
            prefix = "Copied to clipboard! " if action == "copy" else ""
            assert (
                str(output.render())
                == f"{prefix}Code: {expected_code()} (valid for 1s)"
            )
            if action == "copy":
                assert copied == [expected_code()]
            clock[0] = period
            await pilot.pause(0.35)
            assert str(output.render()) == "Code expired. Generate or copy a new code."
            assert len(copied) == (1 if action == "copy" else 0)
            await pilot.click("#copy")
            assert copied[-1] == expected_code()
            assert str(output.render()) == (
                f"Copied to clipboard! Code: {expected_code()} (valid for {period}s)"
            )
            clock[0] += 2
            app._update_validity()
            assert str(output.render()).endswith(f"(valid for {period - 2}s)")

    asyncio.run(check())
    assert entry.model_dump() == before


def test_selection_change_clears_previous_code_and_copy_failure_stays_visible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entries = [
        TotpEntry(account_name=str(index), secret="MY======") for index in range(2)
    ]
    app = make_app(monkeypatch, entries)
    monkeypatch.setattr("desktop_2fa.ui_textual.app.time.time", lambda: 29)

    def fail_copy(value: str) -> None:
        raise RuntimeError("synthetic clipboard unavailable")

    monkeypatch.setattr("pyperclip.copy", fail_copy)

    async def check() -> None:
        async with app.run_test() as pilot:
            await pilot.click("#generate")
            output = app.query_one("#output", Label)
            assert str(output.render()).startswith("Code: ")
            app.query_one("#accounts", ListView).index = 1
            await pilot.pause()
            assert (
                str(output.render())
                == "Selection changed. Generate or copy a new code."
            )
            await pilot.click("#copy")
            assert (
                str(output.render()) == "Copy failed: synthetic clipboard unavailable"
            )
            app._update_validity()
            assert (
                str(output.render()) == "Copy failed: synthetic clipboard unavailable"
            )

    asyncio.run(check())
