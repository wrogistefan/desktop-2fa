import time
from dataclasses import dataclass

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView

from desktop_2fa.totp.generator import generate
from desktop_2fa.utils.base32 import InvalidSecret
from desktop_2fa.vault import Vault
from desktop_2fa.vault.models import TotpEntry
from desktop_2fa.vault.vault import VaultError


@dataclass(frozen=True)
class DisplayedCode:
    index: int
    counter: int
    code: str
    copied: bool


class D2FAApp(App[object]):
    CSS_PATH = "styles.css"
    TITLE = "Desktop-2FA (Textual Prototype)"
    SUB_TITLE = "TOTP Vault UI"

    def __init__(
        self, vault_path: str, password: str, *, raise_load_errors: bool = False
    ):
        super().__init__()
        self.vault_path = vault_path
        self.vault: Vault | None = None
        self.error: str | None = None
        self._displayed_code: DisplayedCode | None = None
        try:
            self.vault = Vault.load(vault_path, password)
        except VaultError as e:
            if raise_load_errors:
                raise
            self.error = f"Unable to load vault: {e}"

    def _entry_label(self, entry: TotpEntry) -> str:
        name = entry.account_name or "(no name)"
        issuer = entry.issuer or ""
        if issuer:
            return f"{name} ({issuer})"
        return name

    def _generate_code(self, entry: TotpEntry, timestamp: int | None = None) -> str:
        return generate(
            entry.secret,
            timestamp=timestamp,
            digits=entry.digits,
            period=entry.period,
            algorithm=entry.algorithm,
        )

    def _copy_to_clipboard(self, code: str) -> bool:
        try:
            import pyperclip
        except ImportError:
            self.query_one("#output", Label).update("pyperclip is not installed")
            return False
        try:
            pyperclip.copy(code)
        except Exception as e:
            self.query_one("#output", Label).update(f"Copy failed: {e}")
            return False
        return True

    def on_mount(self) -> None:
        self.set_interval(0.25, self._update_validity)

    def _update_validity(self, timestamp: int | None = None) -> None:
        displayed = self._displayed_code
        if displayed is None or self.vault is None:
            return
        output = self.query_one("#output", Label)
        if self.query_one("#accounts", ListView).index != displayed.index:
            self._displayed_code = None
            output.update("Selection changed. Generate or copy a new code.")
            return
        entry = self.vault.entries[displayed.index]
        now = int(time.time()) if timestamp is None else timestamp
        if now // entry.period != displayed.counter:
            self._displayed_code = None
            output.update("Code expired. Generate or copy a new code.")
            return
        remaining = entry.period - now % entry.period
        prefix = "Copied to clipboard! " if displayed.copied else ""
        output.update(f"{prefix}Code: {displayed.code} (valid for {remaining}s)")

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        self._update_validity()

    def compose(self) -> ComposeResult:
        yield Header()
        if self.error:
            yield Container(
                Label(self.error, id="message", markup=False),
                Label("", id="output", markup=False),
            )
        elif not self.vault or not self.vault.entries:
            yield Container(
                Label("Vault is empty", id="message", markup=False),
                Label("", id="output", markup=False),
            )
        else:
            yield Container(
                Label("Accounts", id="title", markup=False),
                ListView(
                    *[
                        ListItem(Label(self._entry_label(entry), markup=False))
                        for entry in self.vault.entries
                    ],
                    id="accounts",
                ),
                Button("Generate Code", id="generate"),
                Button("Copy Code", id="copy"),
                Label("", id="output", markup=False),
            )
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if self.error:
            self.query_one("#output", Label).update(self.error)
            return

        if self.vault is None:
            self.query_one("#output", Label).update("Vault not loaded")
            return

        if not self.vault.entries:
            self.query_one("#output", Label).update("Vault is empty")
            return

        button_id = event.button.id
        selected = self.query_one("#accounts", ListView).index

        if selected is None:
            self.query_one("#output", Label).update("No entry selected")
            return

        entry = self.vault.entries[selected]

        if button_id in {"generate", "copy"}:
            self._displayed_code = None
            timestamp = int(time.time())
            try:
                code = self._generate_code(entry, timestamp=timestamp)
            except InvalidSecret:
                self.query_one("#output", Label).update(
                    "Invalid TOTP secret. Repair this entry using the CLI."
                )
                return
            copied = button_id == "copy"
            if copied and not self._copy_to_clipboard(code):
                return
            self._displayed_code = DisplayedCode(
                selected, timestamp // entry.period, code, copied
            )
            self._update_validity(timestamp)


def run_textual(vault_path: str, password: str) -> None:
    app = D2FAApp(vault_path, password, raise_load_errors=True)
    app.run()
