"""Headless end-to-end UI tests; all vaults and passwords are synthetic."""

import asyncio
from pathlib import Path

import pytest
from textual.widgets import Button, Checkbox, Input, Label, ListView

from desktop_2fa.ui_textual.app import D2FAApp
from desktop_2fa.ui_textual.forms import OperationForm
from desktop_2fa.vault import Vault

PASSWORD = "synthetic-form-password"
SECRET = "JBSWY3DPEHPK3PXP"


async def complete_form(
    app: D2FAApp, values: dict[str, str], checked: tuple[str, ...] = ()
) -> None:
    form = app.screen
    assert isinstance(form, OperationForm)
    for key, value in values.items():
        form.query_one(f"#{key}", Input).value = value
    for key in checked:
        form.query_one(f"#{key}", Checkbox).value = True
    form.submit()
    await app.workers.wait_for_complete()
    # Worker completion is an explicit condition, not an assumed KDF duration.
    async with asyncio.timeout(20):
        while app.screen is form:
            await asyncio.sleep(0.05)
            if not form.busy and str(form.query_one("#form-error", Label).render()):
                pytest.fail(str(form.query_one("#form-error", Label).render()))


def test_ui_manages_vault_from_creation_to_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "desktop_2fa.ui_textual.operations.helpers.load_config", lambda: {}
    )
    path = tmp_path / "synthetic.bin"
    app = D2FAApp(str(path), allow_weak_passwords=True)

    async def check() -> None:
        async with app.run_test(size=(110, 42)) as pilot:
            await pilot.pause()
            assert app.vault is None
            await pilot.click("#create")
            await complete_form(
                app, {"new-password": PASSWORD, "confirm-password": PASSWORD}
            )
            assert path.is_file()
            await pilot.pause()
            await pilot.click("#add")
            await complete_form(
                app,
                {
                    "name": "Synthetic GitHub",
                    "issuer": "GitHub",
                    "secret": SECRET,
                    "password": PASSWORD,
                },
            )
            await pilot.pause()
            assert app.vault is not None and len(app.vault.entries) == 1
            assert app._displayed_code is not None
            await pilot.click("#rename")
            await complete_form(app, {"name": "Synthetic work", "password": PASSWORD})
            assert app.vault.entries[0].issuer == "Synthetic work"
            await pilot.pause()
            await pilot.click("#backup")
            await complete_form(app, {"password": PASSWORD})
            assert path.with_suffix(".backup.bin").is_file()
            await pilot.pause()
            exported = tmp_path / "export.bin"
            await pilot.click("#export")
            await complete_form(app, {"file": str(exported), "password": PASSWORD})
            await pilot.pause()
            await pilot.click("#change-password")
            new_password = "synthetic-changed-password"
            await complete_form(
                app,
                {
                    "password": PASSWORD,
                    "new-password": new_password,
                    "confirm-password": new_password,
                },
            )
            assert (
                Vault.load(path, new_password).entries[0].account_name
                == "Synthetic work"
            )
            await pilot.pause()
            await pilot.click("#remove")
            await complete_form(app, {"password": new_password}, ("confirm",))
            assert not app.vault.entries
            await pilot.pause()
            await pilot.click("#import")
            await complete_form(
                app, {"file": str(exported), "password": PASSWORD}, ("overwrite",)
            )
            assert len(app.vault.entries) == 1
            await pilot.press("ctrl+l")
            await pilot.pause()
            assert app.vault is None
            assert app._displayed_code is None
            assert not list(app.query("#accounts Label"))
            assert str(app.query_one("#code", Label).render()) == "------"
            await pilot.click("#unlock")
            await complete_form(app, {"password": PASSWORD})
            assert app.vault is not None

    asyncio.run(check())


def test_failed_form_is_sanitized_and_clears_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from desktop_2fa.ui_textual import forms

    marker = "synthetic-sensitive-exception-marker"

    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError(marker)

    monkeypatch.setattr(forms, "perform", fail)
    app = D2FAApp(str(tmp_path / "not-opened.bin"))

    async def check() -> None:
        async with app.run_test(size=(80, 24)) as pilot:
            app.open_form("unlock")
            await pilot.pause()
            form = app.screen
            form.query_one("#password", Input).value = PASSWORD
            form.query_one("#submit", Button).press()
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert (
                str(form.query_one("#form-error", Label).render())
                == "Operation failed."
            )
            assert form.query_one("#password", Input).value == ""
            assert marker not in app.export_screenshot()
            await pilot.press("escape")
            assert not isinstance(app.screen, OperationForm)

    asyncio.run(check())


def test_search_selects_original_row_and_copy_only_hides_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault = Vault()
    vault.add_entry("first", "Example", SECRET)
    vault.add_entry("second", "Other", SECRET, algorithm="SHA256", digits=8, period=45)
    monkeypatch.setattr(Vault, "load", lambda *args: vault)
    copied: list[str] = []
    monkeypatch.setattr("pyperclip.copy", copied.append)
    app = D2FAApp("synthetic-not-opened", PASSWORD)

    async def check() -> None:
        async with app.run_test(size=(110, 38)) as pilot:
            app.query_one("#search", Input).value = "other"
            await pilot.pause()
            assert app.selected_index == 1
            assert len(app.query_one("#accounts", ListView).children) == 1
            await pilot.click("#copy-only")
            assert len(copied) == 1 and len(copied[0]) == 8
            await pilot.pause(0.35)
            assert app._displayed_code is None
            assert str(app.query_one("#code", Label).render()) == "------"
            await pilot.press("ctrl+l")
            await pilot.pause()
            assert app.vault is None

    asyncio.run(check())


def test_slow_clipboard_cannot_restore_a_locked_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import threading

    started = threading.Event()
    release = threading.Event()
    vault = Vault()
    vault.add_entry("synthetic", "Example", SECRET)
    monkeypatch.setattr(Vault, "load", lambda *args: vault)

    def slow_copy(value: str) -> None:
        started.set()
        assert release.wait(5)

    monkeypatch.setattr("pyperclip.copy", slow_copy)
    app = D2FAApp("synthetic-not-opened", PASSWORD)

    async def check() -> None:
        async with app.run_test(size=(110, 38)) as pilot:
            await pilot.pause()
            try:
                app.query_one("#copy", Button).press()
                async with asyncio.timeout(5):
                    while not started.is_set():
                        await asyncio.sleep(0.01)
                await pilot.press("ctrl+l")
                await pilot.pause()
                assert app.vault is None
            finally:
                release.set()
            await app.workers.wait_for_complete()
            assert app._displayed_code is None
            assert str(app.query_one("#code", Label).render()) == "------"
            assert str(app.query_one("#output", Label).render()) == ""

    asyncio.run(check())


def test_busy_file_worker_keeps_timer_running_and_prevents_cancel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import threading

    from desktop_2fa.ui_textual import forms
    from desktop_2fa.ui_textual.operations import Result

    started = threading.Event()
    release = threading.Event()
    vault = Vault()
    vault.add_entry("synthetic", "Example", SECRET)
    monkeypatch.setattr(Vault, "load", lambda *args: vault)
    clock = [29]
    monkeypatch.setattr("desktop_2fa.ui_textual.app.time.time", lambda: clock[0])

    def slow_operation(*args: object, **kwargs: object) -> Result:
        started.set()
        assert release.wait(5)
        return Result(vault, "Synthetic operation complete.")

    monkeypatch.setattr(forms, "perform", slow_operation)
    app = D2FAApp("synthetic-not-opened", PASSWORD)

    async def check() -> None:
        async with app.run_test(size=(110, 38)) as pilot:
            await pilot.pause()
            app.open_form("backup")
            await pilot.pause()
            form = app.screen
            assert isinstance(form, OperationForm)
            form.query_one("#password", Input).value = PASSWORD
            form.submit()
            try:
                async with asyncio.timeout(5):
                    while not started.is_set():
                        await asyncio.sleep(0.01)
                clock[0] = 30
                await pilot.pause(0.35)
                assert app._displayed_code and app._displayed_code.counter == 1
                await pilot.press("escape", "ctrl+q")
                assert app.screen is form and app.busy
                assert form.query_one("#password", Input).value == ""
            finally:
                release.set()
            await app.workers.wait_for_complete()

    asyncio.run(check())


def test_unexpected_ui_error_never_renders_traceback_locals(
    capsys: pytest.CaptureFixture[str],
) -> None:
    marker = "synthetic-private-exception-marker"
    app = D2FAApp("synthetic-not-opened")

    async def check() -> None:
        with pytest.raises(RuntimeError, match=marker):
            async with app.run_test() as pilot:
                await pilot.pause()
                app._handle_exception(RuntimeError(marker))

    asyncio.run(check())
    captured = capsys.readouterr()
    assert marker not in captured.out + captured.err
    assert app.return_code == 1


def test_auto_lock_closes_forms_clears_secrets_and_defers_busy_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vault = Vault()
    vault.add_entry("synthetic", "Example", SECRET)
    monkeypatch.setattr(Vault, "load", lambda *args: vault)
    app = D2FAApp("synthetic-not-opened", PASSWORD)

    async def check() -> None:
        async with app.run_test(size=(110, 38)) as pilot:
            await pilot.pause()
            app.open_form("add")
            await pilot.pause()
            form = app.screen
            assert isinstance(form, OperationForm)
            secret_field = form.query_one("#secret", Input)
            password_field = form.query_one("#password", Input)
            secret_field.value = SECRET
            password_field.value = PASSWORD
            deadline = app._last_activity + app.AUTO_LOCK_SECONDS
            await app._check_inactivity(deadline - 0.01)
            assert app.vault is not None
            app.busy = True
            await app._check_inactivity(deadline + 1)
            assert app.screen is form and app.vault is not None
            app.busy = False
            await app._check_inactivity(deadline + 1)
            await pilot.pause()
            assert app.vault is None and app._displayed_code is None
            assert app.screen is not form
            assert secret_field.value == ""
            assert password_field.value == ""
            assert not list(app.query("#accounts Label"))

    asyncio.run(check())


def test_keyboard_mouse_and_paste_extend_inactivity_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from textual import events

    vault = Vault()
    vault.add_entry("synthetic", "Example", SECRET)
    monkeypatch.setattr(Vault, "load", lambda *args: vault)
    app = D2FAApp("synthetic-not-opened", PASSWORD)

    async def check() -> None:
        async with app.run_test(size=(110, 38)) as pilot:
            await pilot.pause()
            app.open_form("add")
            await pilot.pause()
            form = app.screen
            form.query_one("#name", Input).focus()
            app._last_activity = 1
            await pilot.press("x")
            assert app._last_activity > 1
            app._last_activity = 1
            await app.on_event(events.Paste("synthetic-paste"))
            assert app._last_activity > 1
            app._last_activity = 1
            await pilot.click("#issuer")
            assert app._last_activity > 1
            previous = app._last_activity
            await pilot.pause(0.35)
            assert app._last_activity == previous
            await pilot.press("ctrl+l")
            await pilot.pause()
            assert app.vault is None and app.screen is not form

    asyncio.run(check())


def test_inactivity_also_clears_password_in_locked_unlock_form() -> None:
    app = D2FAApp("synthetic-not-opened")

    async def check() -> None:
        async with app.run_test(size=(110, 38)) as pilot:
            app.open_form("unlock")
            await pilot.pause()
            field = app.screen.query_one("#password", Input)
            field.value = PASSWORD
            await app._check_inactivity(app._last_activity + app.AUTO_LOCK_SECONDS)
            await pilot.pause()
            assert app.vault is None
            assert field.value == ""
            assert not isinstance(app.screen, OperationForm)

    asyncio.run(check())
