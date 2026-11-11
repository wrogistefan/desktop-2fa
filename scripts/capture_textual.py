"""Capture the unreleased Textual UI using only temporary synthetic data.

Run: python -m scripts.capture_textual --output assets/screenshots/textual-ui
The system clipboard and user configuration are never accessed. SVG captures
come from Textual's headless driver; PNG rendering is a separate local step.
"""

import argparse
import asyncio
import json
import os
import platform
import tempfile
from pathlib import Path
from unittest.mock import patch

from textual.widgets import Button, Checkbox, Input, Label, ListView

from desktop_2fa.ui_textual.app import D2FAApp
from desktop_2fa.ui_textual.forms import OperationForm
from desktop_2fa.vault import Vault
from scripts.release_cli import save_svg

PASSWORD = "synthetic-demo-passphrase-for-captures"
SECRET = "JBSWY3DPEHPK3PXP"
DEMO_CLOCK = [1_700_000_010]


async def campaign(output: Path) -> dict[str, object]:
    cases: list[str] = []
    captures: list[str] = []
    clock = DEMO_CLOCK
    clipboard: list[str] = []
    app = D2FAApp("demo-vault.bin", allow_weak_passwords=True)

    async with app.run_test(size=(110, 38)) as pilot:

        async def capture(name: str) -> None:
            await pilot.pause()
            save_svg(
                output / f"{name}.svg",
                app.export_screenshot(
                    title="Desktop-2FA | SYNTHETIC DEMO / Unreleased UI"
                ),
            )
            captures.append(name)

        async def submit(
            operation: str, values: dict[str, str], checks: tuple[str, ...] = ()
        ) -> None:
            if not isinstance(app.screen, OperationForm):
                app.open_form(operation)
                await pilot.pause()
            form = app.screen
            assert isinstance(form, OperationForm) and form.operation == operation
            for key, value in values.items():
                form.query_one(f"#{key}", Input).value = value
            for key in checks:
                form.query_one(f"#{key}", Checkbox).value = True
            form.query_one("#submit", Button).focus()
            await pilot.press("enter")
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert not isinstance(
                app.screen, OperationForm
            ), "Form operation did not complete"
            cases.append(operation)

        await capture("01-locked")
        app.open_form("create")
        await pilot.pause()
        app.screen.query_one("#new-password", Input).value = PASSWORD
        app.screen.query_one("#confirm-password", Input).value = PASSWORD
        await capture("02-create-vault")
        await submit("create", {"new-password": PASSWORD, "confirm-password": PASSWORD})
        await submit(
            "add",
            {
                "name": "demo@example.invalid",
                "issuer": "GitHub",
                "secret": SECRET,
                "password": PASSWORD,
            },
        )
        await submit(
            "add",
            {
                "uri": f"otpauth://totp/Example%20Cloud:work%40example.invalid?secret={SECRET}&issuer=Example%20Cloud&algorithm=SHA256&digits=8&period=45",
                "password": PASSWORD,
            },
        )
        assert app.vault is not None and len(app.vault.entries) == 2
        app.main_screen.query_one("#accounts", ListView).index = 1
        await capture("03-accounts")
        app.open_form("add")
        await pilot.pause()
        app.screen.query_one("#name", Input).value = "personal@example.invalid"
        app.screen.query_one("#issuer", Input).value = "Example Mail"
        app.screen.query_one("#secret", Input).value = SECRET
        await capture("04-add-account")
        await pilot.press("escape")
        clock[0] = (clock[0] // 45) * 45 + 43
        app._update_validity()
        await capture("05-code-expiring")
        counter = app._displayed_code.counter if app._displayed_code else None
        clock[0] += 2
        app._update_validity()
        assert app._displayed_code and app._displayed_code.counter != counter
        assert not clipboard
        cases.append(
            "automatic refresh across period boundary without clipboard writes"
        )
        with patch("pyperclip.copy", clipboard.append):
            app.main_screen.query_one("#copy-only", Button).focus()
            await pilot.press("enter")
        assert len(clipboard) == 1
        assert str(app.main_screen.query_one("#code", Label).render()) == "------"
        cases.append("copy-only with synthetic clipboard stub")
        await submit("backup", {"password": PASSWORD})
        assert Path("demo-vault.backup.bin").exists()
        await capture("06-encrypted-backup")
        await submit("export", {"file": "demo-export.bin", "password": PASSWORD})
        app.open_form("change-password")
        await capture("07-change-password")
        replacement = "synthetic-replacement-demo-passphrase"
        await submit(
            "change-password",
            {
                "password": PASSWORD,
                "new-password": replacement,
                "confirm-password": replacement,
            },
        )
        await submit("rename", {"name": "Renamed demo", "password": replacement})
        await submit("remove", {"password": replacement}, ("confirm",))
        assert app.vault and len(app.vault.entries) == 1
        await submit(
            "import", {"file": "demo-export.bin", "password": PASSWORD}, ("overwrite",)
        )
        assert app.vault and len(app.vault.entries) == 2
        await pilot.press("ctrl+l")
        await pilot.pause()
        assert app.vault is None and app._displayed_code is None
        assert not list(app.main_screen.query("#accounts Label"))
        cases.append("manual lock removes accounts and displayed code")
        await submit("unlock", {"password": PASSWORD})
        assert Vault.load("demo-vault.bin", PASSWORD).data == app.vault.data
        app.main_screen.query_one("#search", Input).value = "cloud"
        await pilot.pause()
        assert app.selected_index == 1
        cases.append("filtered selection retains original row identity")
        await pilot.resize_terminal(80, 24)
        await capture("08-compact")
        await app._check_inactivity(app._last_activity + app.AUTO_LOCK_SECONDS + 1)
        assert app.vault is None and app._displayed_code is None
        cases.append(
            "five-minute inactivity lock using a controlled monotonic deadline"
        )
        await capture("09-auto-locked")
    return {
        "feature": "Unreleased Textual UI",
        "platform": platform.system(),
        "python": platform.python_version(),
        "passed": len(cases),
        "cases": cases,
        "captures": captures,
        "limitations": [
            "Synthetic accounts, secrets, passwords and controlled clock only",
            "Textual headless driver, not a native desktop/TTY capture",
            "System clipboard replaced by a stub; native clipboard is not verified",
            "No claim of macOS/Linux validation from this Windows campaign",
            "SVG files are rendered screens; optional PNGs use a local browser",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    original = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="d2fa-ui-capture-") as temporary:
        try:
            os.chdir(temporary)
            with (
                patch.dict(os.environ),
                patch(
                    "desktop_2fa.ui_textual.app.time.time",
                    side_effect=lambda: DEMO_CLOCK[0],
                ),
                patch(
                    "desktop_2fa.ui_textual.operations.helpers.load_config",
                    return_value={},
                ),
            ):
                os.environ.pop("NO_COLOR", None)
                report = asyncio.run(campaign(output))
        finally:
            os.chdir(original)
    (output / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"{report['passed']} synthetic UI checks passed; {len(report['captures'])} captures saved."
    )


if __name__ == "__main__":
    main()
