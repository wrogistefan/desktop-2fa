# Desktop-2FA 0.10.0 captures

English, dark-terminal captures for **Desktop-2FA 0.10.0**, made on Windows
with Python 3.13.11. All accounts, passwords and vaults are synthetic. Displayed
codes are temporary values from public example secrets, not real credentials.

PNG files are suitable for README and website reuse; corresponding SVG files
retain scalable text. `report.json` lists each successful check, its expected
exit status and its driver. Terminal images replay actual captured command
output through Rich; their window decorations are rendered, not an operating
system desktop capture. Textual exports its actual headless screen.

| Capture | Demonstrates |
| --- | --- |
| [accounts.png](accounts.png) | Version, initialization, listing with indices |
| [interactive.png](interactive.png) | Interactive add with hidden secret |
| [codes.png](codes.png) | Human-readable, raw and JSON output |
| [rename.png](rename.png) | Rename and collision refusal |
| [recovery.png](recovery.png) | Backup, encrypted export, overwrite refusal, import |
| [textual.png](textual.png) | Mounted Textual prototype with synthetic accounts |

## Reproduce

From the checkout root, using the existing editable development installation:

```powershell
.venv/Scripts/python.exe scripts/release_cli.py
.venv/Scripts/python.exe scripts/render_cli_captures.py --browser "C:/Program Files/Google/Chrome/Application/chrome.exe" assets/screenshots/release-0.10.0
```

The campaign invokes the installed `d2fa` and `desktop-2fa` entry points. It
uses explicit vault paths, password files and a temporary home. Its public
password file is copied from the [demo fixture](../../../tests/fixtures/release/README.md).
Vault files and
password files are removed with the temporary directory; the report contains
case names/statuses, not their contents. The renderer uses a temporary browser
profile and local files. Edge did not produce an image on this machine; Chrome
did. Browser launch may require environment permission.

Interactive prompts use CliRunner with interactivity enabled; password change
uses a stub for getpass. Clipboard success/failure use a stub and never touch
the system clipboard. Textual mounts through `ui` using its headless test
driver. Separately, native Windows terminal checks passed hidden password
initialization, hidden-secret interactive add and password change/reopen.
Their generated vault/password files were removed. System clipboard and native
UI/display checks on Linux and macOS remain manual. Live TOTP values and validity
seconds vary between runs. Check subprocess statuses; only a completed
successful campaign writes a new report.

The version/policy flag shown in captures is for these synthetic examples;
keep strong passwords for real vaults.
