from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer, ListView, ListItem, Label, Button

from desktop_2fa.vault import Vault
from desktop_2fa.totp import generate_totp


class D2FAApp(App):
    CSS_PATH = "styles.css"
    TITLE = "Desktop-2FA (Textual Prototype)"
    SUB_TITLE = "TOTP Vault UI"

    def __init__(self, vault_path: str):
        super().__init__()
        self.vault_path = vault_path
        self.vault = Vault.load(vault_path)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("Accounts", id="title"),
            ListView(
                *[
                    ListItem(Label(entry.name))
                    for entry in self.vault.entries
                ],
                id="accounts"
            ),
            Button("Generate Code", id="generate"),
            Button("Copy Code", id="copy"),
            Label("", id="output")
        )
        yield Footer()

    async def on_button_pressed(self, event):
        button_id = event.button.id
        selected = self.query_one("#accounts").index

        if selected is None:
            self.query_one("#output").update("No entry selected")
            return

        entry = self.vault.entries[selected]

        if button_id == "generate":
            code = generate_totp(entry.secret)
            self.query_one("#output").update(f"Code: {code}")

        if button_id == "copy":
            code = generate_totp(entry.secret)
            import pyperclip
            pyperclip.copy(code)
            self.query_one("#output").update("Copied to clipboard!")


def run_textual(vault_path: str):
    app = D2FAApp(vault_path)
    app.run()
