# Unreleased Textual UI captures

Real Textual screens from the repository's unreleased UI, captured with its
headless driver. All accounts, passwords, provisioning secrets and codes are
synthetic. The UI uses a controlled clock. These captures supersede neither the
historical 0.10.0 assets nor the published package's feature description.

| Image | Demonstrated behavior |
| --- | --- |
| [01-locked.png](01-locked.png) | Explicit unlock, create and encrypted import choices. |
| [02-create-vault.png](02-create-vault.png) | Masked password confirmation and overwrite consent. |
| [03-accounts.png](03-accounts.png) | Searchable rows, live TOTP code, parameter display and countdown. |
| [04-add-account.png](04-add-account.png) | Manual provisioning and masked secret/URI input. |
| [05-code-expiring.png](05-code-expiring.png) | Last seconds of the selected entry's actual period. |
| [06-encrypted-backup.png](06-encrypted-backup.png) | Successful encrypted backup after password authentication. |
| [07-change-password.png](07-change-password.png) | Existing/new password fields and confirmation. |
| [08-compact.png](08-compact.png) | 80×24 terminal with scrolling. |
| [09-auto-locked.png](09-auto-locked.png) | Automatic lock after five minutes, exercised with a controlled deadline. |

Matching SVG files are included for scalable documentation/marketing use.
The window frame is Rich's SVG export decoration, not a native operating-system
window. PNGs are local browser renders of those SVGs. Marketing must identify
this as the unreleased terminal UI, not a shipped GUI or a new public release.

Reproduce from the repository root with the project environment:

```powershell
.venv/Scripts/python.exe -m scripts.capture_textual --output assets/screenshots/textual-ui
.venv/Scripts/python.exe -m scripts.render_cli_captures --browser 'C:/Program Files/Google/Chrome/Application/chrome.exe' assets/screenshots/textual-ui
```

The campaign creates its vaults in a temporary directory, never uses the default
vault, replaces configuration loading with an empty synthetic configuration,
and stubs clipboard writes. `NO_COLOR` is removed only inside the capture tool
so the images demonstrate the dark palette. Runtime UI still respects the
terminal's no-color preference. The tool rewrites only its named capture outputs.

[report.json](report.json) records the exercised scenarios and limitations.
Headless tests and captures do not prove native clipboard behavior, native TTY
rendering or macOS/Linux behavior. See the [UI guide](../../../docs/user_manual.md#textual-terminal-ui)
and [threat analysis](../../../docs/textual-security.md).
