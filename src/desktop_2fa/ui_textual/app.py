import asyncio
import time
from dataclasses import dataclass

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    ProgressBar,
)

from desktop_2fa.cli.errors import describe_error
from desktop_2fa.totp.generator import generate
from desktop_2fa.ui_textual.forms import OperationForm
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
    TITLE = "Desktop-2FA"
    SUB_TITLE = "Own your vault. Generate your codes offline."
    AUTO_LOCK_SECONDS = 5 * 60
    BINDINGS = [
        Binding("ctrl+l", "lock", "Lock", priority=True),
        Binding("ctrl+n", "add", "Add account"),
        Binding("ctrl+b", "backup", "Backup"),
        Binding("ctrl+q", "quit", "Quit", priority=True),
    ]

    def __init__(
        self,
        vault_path: str,
        password: str | None = None,
        *,
        raise_load_errors: bool = False,
        allow_weak_passwords: bool = False,
    ) -> None:
        super().__init__()
        self.vault_path = vault_path
        self.allow_weak_passwords = allow_weak_passwords
        self.vault: Vault | None = None
        self.error: str | None = None
        self.busy = False
        self._copy_busy = False
        self._code_request = 0
        self._accounts_lock = asyncio.Lock()
        self._refreshing = False
        self._last_activity = time.monotonic()
        self._displayed_code: DisplayedCode | None = None
        self._visible_indices: list[int] = []
        # Optional CLI authentication finishes before the UI event loop starts.
        # The password is never stored in the app.
        if password is not None:
            try:
                self.vault = Vault.load(vault_path, password)
            except VaultError as error:
                if raise_load_errors:
                    raise
                self.error = describe_error(error)[2]

    @property
    def main_screen(self) -> Screen[object]:
        """Keep background queries stable while an operation modal is open."""
        return self.screen_stack[0]

    @property
    def selected_index(self) -> int | None:
        if not self.main_screen.query("#accounts"):
            return None
        index = self.main_screen.query_one("#accounts", ListView).index
        if index is None or not 0 <= index < len(self._visible_indices):
            return None
        return self._visible_indices[index]

    def _entry_label(self, entry: TotpEntry) -> str:
        name = entry.account_name or "(no name)"
        return f"{name} ({entry.issuer})" if entry.issuer else name

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

            pyperclip.copy(code)
        except Exception:
            return False
        return True

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="workspace"):
            yield Label("LOCAL VAULT / OFFLINE TOTP", id="eyebrow", markup=False)
            yield Label(f"Vault: {self.vault_path}", id="vault-path", markup=False)
            yield Label(
                self.error
                or "Unlock an existing vault, create a new one, or import an encrypted backup.",
                id="message",
                markup=False,
            )
            with Horizontal(id="body"):
                with Vertical(id="account-panel"):
                    yield Label("Accounts", id="title", markup=False)
                    yield Input(placeholder="Search accounts or issuers", id="search")
                    yield ListView(id="accounts")
                with VerticalScroll(id="code-panel"):
                    yield Label("YOUR ONE-TIME CODE", classes="muted", markup=False)
                    yield Label(
                        "Select an account", id="selected-account", markup=False
                    )
                    yield Label("------", id="code", markup=False)
                    yield Label("", id="parameters", markup=False)
                    yield ProgressBar(
                        total=30, show_eta=False, show_percentage=False, id="validity"
                    )
                    yield Label("", id="output", markup=False)
                    with Horizontal(classes="code-actions"):
                        yield Button("Generate", id="generate", variant="primary")
                        yield Button("Copy", id="copy")
                        yield Button("Copy only", id="copy-only")
            with VerticalScroll(id="tools"):
                with Horizontal(classes="toolbar"):
                    yield Button("Add account", id="add", variant="primary")
                    yield Button("Rename", id="rename")
                    yield Button("Remove", id="remove", variant="error")
                    yield Button("Lock", id="lock")
                with Horizontal(classes="toolbar"):
                    yield Button("Unlock", id="unlock")
                    yield Button("Create vault", id="create")
                    yield Button("Import", id="import")
                    yield Button("Export", id="export")
                    yield Button("Backup", id="backup")
                    yield Button("Password", id="change-password")
            yield Label(
                "Encrypted on disk / Offline / Auto-lock: 5 min / Ctrl+L to lock",
                id="privacy",
                markup=False,
            )
        yield Footer()

    async def on_mount(self) -> None:
        self.theme = "textual-dark"
        await self._refresh_accounts()
        self._update_controls()
        self.set_interval(0.25, self._update_validity)
        self.set_interval(1, self._check_inactivity)

    async def on_event(self, event: events.Event) -> None:
        # Observe input before focused widgets consume it (including passwords
        # and pasted input). Countdown/timer events must not extend the session.
        if isinstance(event, (events.InputEvent, events.Paste)):
            self._last_activity = time.monotonic()
        await super().on_event(event)

    async def _check_inactivity(self, now: float | None = None) -> None:
        if self.busy or (self.vault is None and len(self.screen_stack) == 1):
            return
        now = time.monotonic() if now is None else now
        if now - self._last_activity >= self.AUTO_LOCK_SECONDS:
            await self.action_lock()
            self.main_screen.query_one("#message", Label).update(
                "Vault locked after 5 minutes of inactivity."
            )

    def _update_controls(self) -> None:
        if not self.main_screen.query("#add"):
            return
        unlocked = self.vault is not None
        for identifier in (
            "add",
            "export",
            "backup",
            "change-password",
            "lock",
            "search",
        ):
            self.main_screen.query_one(f"#{identifier}").disabled = not unlocked
        for identifier in ("rename", "remove", "generate", "copy", "copy-only"):
            self.main_screen.query_one(f"#{identifier}").disabled = (
                self.selected_index is None
            )
        self.main_screen.query_one("#unlock").disabled = unlocked

    async def _refresh_accounts(self) -> None:
        async with self._accounts_lock:
            self._refreshing = True
            try:
                await self._rebuild_accounts()
            finally:
                self._refreshing = False

    async def _rebuild_accounts(self) -> None:
        accounts = self.main_screen.query_one("#accounts", ListView)
        self._displayed_code = None
        self._clear_code()
        await accounts.clear()
        search = self.main_screen.query_one("#search", Input).value.casefold()
        self._visible_indices = (
            [
                index
                for index, entry in enumerate(self.vault.entries)
                if search in self._entry_label(entry).casefold()
            ]
            if self.vault
            else []
        )
        await accounts.extend(
            [
                ListItem(
                    Label(
                        f"{index + 1}. {self._entry_label(self.vault.entries[index])}",
                        markup=False,
                    )
                )
                for index in self._visible_indices
            ]
            if self.vault
            else []
        )
        accounts.index = 0 if self._visible_indices else None
        self._update_controls()
        if self.vault and not self.vault.entries:
            self.main_screen.query_one("#message", Label).update(
                "Vault is empty. Add your first account."
            )
        elif self.vault and not self._visible_indices:
            self.main_screen.query_one("#message", Label).update(
                "No accounts match your search."
            )
        self._show_selection()

    async def show_vault(self, vault: Vault, message: str) -> None:
        if self.vault is None:
            self._last_activity = time.monotonic()
        self.vault = vault
        self.error = None
        self.main_screen.query_one("#search", Input).value = ""
        await self._refresh_accounts()
        if vault.duplicate_account_names:
            message += " Duplicate account names found: select an explicit row and rename it to repair."
        self.main_screen.query_one("#message", Label).update(message)

    def _clear_code(self) -> None:
        self._code_request += 1
        if self.main_screen.query("#code"):
            self.main_screen.query_one("#code", Label).update("------")
            self.main_screen.query_one("#output", Label).update("")
            self.main_screen.query_one("#validity", ProgressBar).update(progress=0)

    def _show_selection(self) -> None:
        index = self.selected_index
        if self.vault is None or index is None:
            self.main_screen.query_one("#selected-account", Label).update(
                "Select an account" if self.vault else "Vault locked"
            )
            self.main_screen.query_one("#parameters", Label).update("")
            return
        entry = self.vault.entries[index]
        self.main_screen.query_one("#selected-account", Label).update(
            self._entry_label(entry)
        )
        self.main_screen.query_one("#parameters", Label).update(
            f"{entry.algorithm} / {entry.digits} digits / {entry.period}s"
        )
        self._display_code(index)

    def _display_code(self, index: int) -> None:
        self._code_request += 1
        if self.vault is None:
            return
        self._displayed_code = None
        timestamp = int(time.time())
        entry = self.vault.entries[index]
        try:
            code = self._generate_code(entry, timestamp)
        except InvalidSecret:
            self._clear_code()
            self.main_screen.query_one("#output", Label).update(
                "Invalid TOTP secret. Add a valid replacement before removing this entry."
            )
            return
        self._displayed_code = DisplayedCode(
            index, timestamp // entry.period, code, False
        )
        self._update_validity(timestamp)

    async def _copy_code(
        self, displayed: DisplayedCode, request: int, period: int, hidden: bool
    ) -> None:
        try:
            copied = await asyncio.to_thread(self._copy_to_clipboard, displayed.code)
            if (
                self._code_request != request
                or self.vault is None
                or self.selected_index != displayed.index
            ):
                return
            if not copied:
                message = (
                    "Copy failed: clipboard unavailable. Try generating a visible code."
                )
            elif int(time.time()) // period != displayed.counter:
                message = "Copied code expired. Copy again for a fresh code."
            elif hidden:
                message = (
                    "Copied to clipboard. Code hidden; clipboard history may retain it."
                )
            else:
                self._displayed_code = DisplayedCode(
                    displayed.index, displayed.counter, displayed.code, True
                )
                self._update_validity()
                return
            self.main_screen.query_one("#output", Label).update(message)
        finally:
            self._copy_busy = False

    def _update_validity(self, timestamp: int | None = None) -> None:
        displayed = self._displayed_code
        if displayed is None or self.vault is None:
            return
        if not self.main_screen.query("#output") or not self.main_screen.query(
            "#accounts"
        ):
            self._displayed_code = None
            return
        if self.selected_index != displayed.index:
            self._displayed_code = None
            self._clear_code()
            return
        entry = self.vault.entries[displayed.index]
        now = int(time.time()) if timestamp is None else timestamp
        if now // entry.period != displayed.counter:
            try:
                code = self._generate_code(entry, now)
            except InvalidSecret:
                self._displayed_code = None
                self._clear_code()
                return
            displayed = DisplayedCode(displayed.index, now // entry.period, code, False)
            self._displayed_code = displayed
        remaining = entry.period - now % entry.period
        prefix = "Copied to clipboard! " if displayed.copied else ""
        self.main_screen.query_one("#code", Label).update(displayed.code)
        self.main_screen.query_one("#code", Label).set_class(remaining <= 5, "expiring")
        self.main_screen.query_one("#output", Label).update(
            f"{prefix}Code: {displayed.code} (valid for {remaining}s)"
        )
        self.main_screen.query_one("#validity", ProgressBar).update(
            total=entry.period, progress=remaining
        )

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if self._refreshing:
            return
        if not self.main_screen.query("#accounts") or not self.main_screen.query(
            "#add"
        ):
            return
        self._update_controls()
        self._clear_code()
        self._show_selection()

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search":
            await self._refresh_accounts()

    async def action_lock(self) -> None:
        if self.busy:
            return
        while len(self.screen_stack) > 1:
            if isinstance(self.screen, OperationForm):
                self.screen.clear_secrets()
            await self.pop_screen()
        self._displayed_code = None
        self.vault = None
        self.error = None
        self.main_screen.query_one("#search", Input).value = ""
        await self._refresh_accounts()
        self.main_screen.query_one("#message", Label).update(
            "Vault locked. Unlock to view accounts."
        )

    def open_form(self, operation: str) -> None:
        if self.busy or len(self.screen_stack) > 1:
            return
        if operation not in {"unlock", "create", "import"} and self.vault is None:
            return
        self.push_screen(OperationForm(self, operation))

    def action_add(self) -> None:
        self.open_form("add")

    def action_backup(self) -> None:
        self.open_form("backup")

    async def action_quit(self) -> None:
        # Do not abandon a write between its publication and UI completion.
        if not self.busy:
            if isinstance(self.screen, OperationForm):
                self.screen.clear_secrets()
            self._displayed_code = None
            self.vault = None
            self.exit()

    def _fatal_error(self) -> None:
        # Textual's default traceback includes local variables, which may hold
        # passwords, provisioning input or decrypted entries. Keep that output
        # behind the same sanitized boundary as CLI failures. run_test still
        # re-raises the stored exception for synthetic regression tests.
        self.exit(
            return_code=1,
            message="Unexpected UI error. Restart the interface and unlock the vault again.",
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        identifier = event.button.id
        if identifier == "lock":
            await self.action_lock()
        elif identifier in {"generate", "copy", "copy-only"}:
            index = self.selected_index
            if index is not None and not self._copy_busy:
                self._display_code(index)
                displayed = self._displayed_code
                if (
                    identifier != "generate"
                    and displayed is not None
                    and self.vault is not None
                ):
                    period = self.vault.entries[index].period
                    self._displayed_code = None
                    self._clear_code()
                    self._copy_busy = True
                    self.run_worker(
                        self._copy_code(
                            displayed,
                            self._code_request,
                            period,
                            identifier == "copy-only",
                        )
                    )
        elif identifier:
            self.open_form(identifier)


def run_textual(
    vault_path: str, password: str | None = None, *, allow_weak_passwords: bool = False
) -> None:
    app = D2FAApp(
        vault_path,
        password,
        raise_load_errors=True,
        allow_weak_passwords=allow_weak_passwords,
    )
    del password
    app.run()
    if app.return_code:
        raise RuntimeError("Textual UI failed")
