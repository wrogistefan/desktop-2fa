"""Keyboard-accessible operation dialogs; secret values are always masked."""

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label

from desktop_2fa.cli.errors import describe_error
from desktop_2fa.ui_textual.operations import FormError, perform

if TYPE_CHECKING:
    from desktop_2fa.ui_textual.app import D2FAApp


TITLES = {
    "unlock": "Unlock vault",
    "create": "Create encrypted vault",
    "add": "Add account",
    "rename": "Rename selected account",
    "remove": "Remove selected account",
    "export": "Export encrypted vault",
    "import": "Import encrypted vault",
    "backup": "Create encrypted backup",
    "change-password": "Change vault password",
}


class OperationForm(ModalScreen[None]):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, owner: "D2FAApp", operation: str) -> None:
        super().__init__()
        self.owner = owner
        self.operation = operation
        self.selected = owner.selected_index
        self.busy = False

    def field(
        self, label: str, identifier: str, *, secret: bool = False
    ) -> ComposeResult:
        yield Label(label, markup=False)
        yield Input(password=secret, id=identifier)

    def compose(self) -> ComposeResult:
        operation = self.operation
        with VerticalScroll(id="dialog"):
            yield Label(TITLES[operation], id="dialog-title", markup=False)
            yield Label(
                f"Vault: {self.owner.vault_path}", classes="muted", markup=False
            )
            if operation in {"rename", "remove"} and self.selected is not None:
                vault = self.owner.vault
                if vault:
                    yield Label(
                        f"Selected #{self.selected + 1}: {self.owner._entry_label(vault.entries[self.selected])}",
                        markup=False,
                    )
            if operation == "add":
                yield Label(
                    "Enter manual fields OR a hidden otpauth URI. URI parameters are preserved.",
                    markup=False,
                )
                yield from self.field("Account name", "name")
                yield from self.field("Issuer", "issuer")
                yield from self.field("Base32 secret", "secret", secret=True)
                yield from self.field(
                    "Provisioning URI (optional, replaces manual fields)",
                    "uri",
                    secret=True,
                )
            if operation == "rename":
                yield Label(
                    "As in the CLI, rename changes both account name and issuer.",
                    markup=False,
                )
                yield from self.field("New account name and issuer", "name")
            if operation in {"export", "import"}:
                yield from self.field(
                    (
                        "Encrypted source file"
                        if operation == "import"
                        else "Encrypted destination file"
                    ),
                    "file",
                )
            if operation == "import":
                yield Label(
                    "D2FA binary only. Replaces the selected vault; does not merge accounts. Enter the SOURCE password.",
                    markup=False,
                )
            if operation == "backup":
                yield Label(
                    "Creates the next available .backup.bin file beside this vault, with the same password.",
                    markup=False,
                )
            if operation != "create":
                yield from self.field(
                    "Source password" if operation == "import" else "Vault password",
                    "password",
                    secret=True,
                )
            if operation in {"create", "change-password"}:
                yield from self.field("New vault password", "new-password", secret=True)
                yield from self.field(
                    "Confirm new password", "confirm-password", secret=True
                )
                yield Checkbox(
                    "I accept a weak password (unless configuration forbids it)",
                    id="weak-password",
                )
            if operation in {"create", "import", "export"}:
                yield Checkbox(
                    "Overwrite existing destination (permanently replaces its contents)",
                    id="overwrite",
                )
            if operation == "remove":
                yield Checkbox("Permanently remove this selected account", id="confirm")
            yield Label("", id="form-error", markup=False)
            with Horizontal(classes="dialog-actions"):
                yield Button(
                    "Confirm" if operation in {"remove", "import"} else "Continue",
                    variant="primary",
                    id="submit",
                )
                yield Button("Cancel", id="cancel")

    def action_cancel(self) -> None:
        if not self.busy:
            self.clear_secrets()
            self.dismiss()

    def clear_secrets(self) -> None:
        for field in self.query(Input):
            if field.password:
                field.value = ""

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "cancel":
            self.action_cancel()
        elif event.button.id == "submit":
            self.submit()

    def submit(self) -> None:
        if self.busy:
            return
        values = {field.id: field.value for field in self.query(Input) if field.id}
        values.update(
            {
                field.id: "yes" if field.value else "no"
                for field in self.query(Checkbox)
                if field.id
            }
        )
        self.clear_secrets()
        self.busy = self.owner.busy = True
        for widget in self.query("Input, Checkbox, Button"):
            widget.disabled = True
        self.query_one("#form-error", Label).update("Working locally…")
        self.run_worker(self.execute(values), exit_on_error=False)

    async def execute(self, values: dict[str, str]) -> None:
        try:
            result = await asyncio.to_thread(
                perform,
                self.operation,
                Path(self.owner.vault_path),
                self.owner.vault,
                self.selected,
                values,
                allow_weak=self.owner.allow_weak_passwords,
            )
            values.clear()
            await self.owner.show_vault(result.vault, result.message)
            self.dismiss()
        except Exception as error:
            message = (
                str(error) if isinstance(error, FormError) else describe_error(error)[2]
            )
            self.query_one("#form-error", Label).update(message)
            for widget in self.query("Input, Checkbox, Button"):
                widget.disabled = False
        finally:
            values.clear()
            self.busy = self.owner.busy = False
