"""Headless prototype regressions with synthetic, in-memory vaults only."""

import asyncio

import pytest
from textual.widgets import Button, Label, ListView

from desktop_2fa.totp.generator import generate
from desktop_2fa.ui_textual.app import D2FAApp
from desktop_2fa.vault import Vault
from desktop_2fa.vault.models import TotpEntry, VaultData


def make_app(monkeypatch: pytest.MonkeyPatch, entries: list[TotpEntry]) -> D2FAApp:
    vault = Vault(VaultData(entries=entries))
    monkeypatch.setattr(Vault, "load", lambda *args: vault)
    return D2FAApp("synthetic-not-opened", "synthetic-password")


@pytest.mark.parametrize(
    ("name", "issuer"),
    [
        ("[/bold]", "[/red]"),
        ("[bold]literal[/bold]", "[link=https://example.invalid]issuer[/link]"),
        ("[] [ brackets", "issuer ]"),
        ("Żółw 🐢 日本語", "Źródło"),
        ("", ""),
        (None, None),
        ("long " * 300, "issuer " * 100),
    ],
)
def test_labels_render_literally_without_breaking_other_entries(
    monkeypatch: pytest.MonkeyPatch, name: str | None, issuer: str | None
) -> None:
    entries = [
        TotpEntry(account_name=name, issuer=issuer, secret="MY======"),
        TotpEntry(account_name="healthy", issuer="Example", secret="MZXQ===="),
    ]
    before = [entry.model_dump() for entry in entries]
    app = make_app(monkeypatch, entries)
    monkeypatch.setattr("desktop_2fa.ui_textual.app.time.time", lambda: 59)

    async def check() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            labels = list(app.query("#accounts Label"))
            expected = name or "(no name)"
            if issuer:
                expected += f" ({issuer})"
            assert str(labels[0].render()) == expected
            assert str(labels[1].render()) == "healthy (Example)"
            app.query_one("#accounts", ListView).index = 1
            await pilot.click("#generate")
            assert str(app.query_one("#output", Label).render()).startswith("Code: ")

    asyncio.run(check())
    assert [entry.model_dump() for entry in entries] == before


def test_selection_generate_and_copy_keep_original_totp_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entries = [
        TotpEntry(account_name="[/bold]", secret="MY======"),
        TotpEntry(
            account_name="[red]literal[/red]",
            issuer="[/red]",
            secret="MZXQ====",
            algorithm="SHA256",
            digits=8,
            period=45,
        ),
    ]
    app = make_app(monkeypatch, entries)
    monkeypatch.setattr("desktop_2fa.totp.generator.time.time", lambda: 59)
    copied: list[str] = []
    monkeypatch.setattr("pyperclip.copy", copied.append)

    async def check() -> None:
        async with app.run_test() as pilot:
            # Repeated activations test parameter parity, not the 0.2s button
            # animation during which Textual deliberately ignores new presses.
            for button in app.query(Button):
                button.active_effect_duration = 0
            for index, entry in enumerate(entries):
                app.query_one("#accounts", ListView).index = index
                await pilot.pause()
                expected = generate(
                    entry.secret,
                    timestamp=59,
                    algorithm=entry.algorithm,
                    digits=entry.digits,
                    period=entry.period,
                )
                # Parameter parity does not depend on pointer coordinates.
                app.query_one("#generate", Button).focus()
                await pilot.pause()
                await pilot.press("enter")
                remaining = entry.period - 59 % entry.period
                assert str(app.query_one("#output", Label).render()) == (
                    f"Code: {expected} (valid for {remaining}s)"
                )
                app.query_one("#copy", Button).focus()
                await pilot.pause()
                await pilot.press("enter")
                assert copied[-1] == expected

    asyncio.run(check())
    assert len(copied) == 2


def test_dynamic_error_messages_are_literal(monkeypatch: pytest.MonkeyPatch) -> None:
    from desktop_2fa.vault.vault import VaultIOError

    def fail_load(*args: object) -> None:
        raise VaultIOError("Synthetic [/bold] [red]file[/red]")

    monkeypatch.setattr(Vault, "load", fail_load)
    app = D2FAApp("synthetic-not-opened", "synthetic-password")

    async def check() -> None:
        async with app.run_test() as pilot:
            assert str(app.query_one("#message", Label).render()) == app.error
            app.query_one("#output", Label).update("[/bold] [red]literal[/red]")
            await pilot.pause()
            assert (
                str(app.query_one("#output", Label).render())
                == "[/bold] [red]literal[/red]"
            )

    asyncio.run(check())
