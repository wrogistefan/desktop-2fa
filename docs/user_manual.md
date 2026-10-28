# Desktop-2FA User Manual

## Overview

Desktop-2FA is a secure, offline two-factor authentication (2FA) manager for desktop environments. It provides a command-line interface for managing TOTP (Time-based One-Time Password) tokens with strong encryption and no cloud dependencies.

## Quick Start

### Installation

```bash
pip install desktop-2fa
```

This manual covers Desktop-2FA 0.9.0. The public Python `Vault.save()` and
`Vault.load()` methods require an explicit, non-empty password. If you created
a passwordless vault through the Python API in an earlier version, open and
re-save it with a non-empty password using that previous version before
upgrading.

### First Use

1. Initialize your vault:
```bash
d2fa init-vault
```

2. Add your first TOTP token:
```bash
d2fa add GitHub GitHub JBSWY3DPEHPK3PXP
```

3. Generate a code:
```bash
d2fa code GitHub
```

## Commands

### Global Options

Place global options before the command:

- `--vault PATH`: Select the vault file (place this global option before the command)
- `--password PASSWORD`: Provide password directly
- `--password-file FILE`: Read password from file
- `--allow-weak-passwords`: Allow weak passwords (bypasses strength checks)
- `--help`: Show help for the command

### Selecting the Vault File

The default vault is `~/.desktop-2fa/vault`. Select another vault for an
individual command by placing the global `--vault` option before the command:

```bash
# List entries in a separate vault
d2fa --vault ./development-vault list

# Initialize the selected vault
d2fa --vault ./development-vault vault init

# Show the selected path in a terminal-safe quoted form
d2fa --vault ./development-vault vault path

# Launch the Textual prototype with the selected vault
d2fa --vault ./development-vault ui
```

Alternatively, set `DESKTOP_2FA_VAULT` to choose the path by default:

```bash
DESKTOP_2FA_VAULT=./development-vault d2fa list
```

An explicit `--vault` takes precedence over `DESKTOP_2FA_VAULT`. If neither is
set, the existing default path is used.

Vault files must be regular files no larger than 10 MiB.
The save limit includes the UTF-8 JSON payload and 49 bytes of encryption and
format overhead. Invalid data or an oversized save leaves the previous vault
unchanged. CLI commands report save-validation errors with status 6. If adding
or renaming an entry exceeds the limit, reduce the stored data before trying again.
Python `Vault.save()` raises `VaultValidationError` (a `ValueError` subclass)
for invalid data or oversized output. Supported legacy entries and D2FA v1
remain compatible; no migration is required.

### `vault init` - Initialize New Vault

Creates a new encrypted vault file.

```bash
d2fa vault init [--force]
```

**Options:**
- `--force`: Overwrite existing vault

**Examples:**
```bash
# Create new vault (interactive password prompt)
d2fa vault init

# Overwrite existing vault
d2fa vault init --force

# Create vault with password from file
d2fa --password-file ~/.vault_pass vault init
```

**Password Strength:** The vault password is evaluated using zxcvbn. If the password is weak:
- In default mode: A warning is shown, and you can confirm to continue
- In strict mode (with `reject_weak_passwords = true`): The weak password is rejected immediately

Example of password strength feedback:
```
Password too weak (score 1 < 3). This is similar to a word by itself. 
Add another word or two. Otherwise, a few variations of this are very guessable.
Continue with weak password? [y/N]:
```

### `list` - List All Entries

Displays all stored TOTP entries.

```bash
d2fa list
```

**Examples:**
```bash
d2fa list
# Output:
# - GitHub (GitHub)
# - AWS (Amazon)
# - Google (personal)
```

### `add` - Add New TOTP Entry

Adds a new TOTP token to the vault.

```bash
d2fa add [NAME] [ISSUER] [SECRET]
```

**Parameters:**
- `NAME`: Unique identifier for the entry (optional in interactive mode)
- `ISSUER`: Name of the service/provider (optional in interactive mode)
- `SECRET`: Base32-encoded secret key (optional in interactive mode)

**Interactive Mode:**
When run in a terminal without arguments, prompts for name, issuer and secret:
```bash
d2fa add
Name (unique identifier): GitHub
Issuer: GitHub
Secret: JBSWY3DPEHPK3PXP
```

**Examples:**
```bash
# Add entry interactively (prompts for missing values)
d2fa add

# Add with arguments
d2fa add GitHub GitHub JBSWY3DPEHPK3PXP

# Add using otpauth URL
d2fa add "otpauth://totp/GitHub:user?secret=JBSWY3DPEHPK3PXP&issuer=GitHub"

# Add with password from command line
d2fa --password mypassword add GitHub GitHub JBSWY3DPEHPK3PXP
```

Provisioning URIs retain `algorithm`, `digits` and `period` after saving and
loading. Defaults are SHA1, 6 digits and 30 seconds. Algorithms SHA1/SHA256/SHA512
are accepted case-insensitively; periods must be positive integers. Desktop-2FA
supports 6, 7 or 8 digits (7 is an extension to the linked Key URI format).
Percent-encoded labels are decoded, including an encoded issuer/account colon.
The issuer query parameter takes precedence when no prefix exists; if both are
present they must agree. A label without a prefix or issuer query retains its
legacy behavior of using the label for both issuer and account name.

Both the single-URI syntax above and `d2fa add NAME "otpauth://..."` are
supported. The URI label supplies the account name in either case. Do not
combine a URI with a separate secret. At the interactive issuer prompt, paste
the URI and no separate secret is requested. Base32 URI secrets are normalized
to uppercase with padding as needed, preserving decoded secret bytes.

Invalid algorithms, digit counts, periods, missing/invalid secrets, conflicting
issuers, duplicate recognized parameters, HOTP/counter data, fragments and
malformed label encodings are rejected before vault creation or modification.
These provisioning errors exit with status 6. Unknown extension query parameters
are ignored. See [Key URI Format](https://github.com/google/google-authenticator/wiki/Key-Uri-Format).

**Notes:**
- `name` is the unique identifier used in CLI commands (e.g., `d2fa code GitHub`)
- `issuer` is a display label and may repeat across entries
- Names must be unique within the vault
- Older versions allowed duplicate names; you may see warnings about this when loading existing vaults
- Use `d2fa list --indices` and `d2fa rename OLD NEW --index N` to repair duplicates
- Secrets must be valid Base32
- otpauth URLs are automatically parsed
- If vault doesn't exist, it will be created automatically
- In interactive mode, the secret is entered visibly (not hidden)

### `vault unlock` - Unlock and Verify Vault

Unlocks an existing vault and checks if the password is weak (if configured).

```bash
d2fa vault unlock
```

**Examples:**
```bash
# Unlock vault with interactive password prompt
d2fa vault unlock
# Output: Vault unlocked successfully.

# Unlock with password provided
d2fa --password mypassword vault unlock
# Output: Vault unlocked successfully.
# (If vault password is weak and warn_on_weak_existing_passwords is true)
# Warning: Your vault password is weak (score 1). Consider changing it.
```

**Notes:**
- This command verifies vault access and checks password strength
- If `warn_on_weak_existing_passwords = true` in config and the password is weak, a non-blocking warning is displayed

### `vault change-password` - Change Vault Password

Changes the vault password. The new password is validated for strength.

```bash
d2fa vault change-password
```

**Examples:**
```bash
# Change vault password (interactive)
d2fa vault change-password
# Output: 
# Old vault password:
# New vault password:
# Confirm new vault password:
# Vault password changed successfully.

# Change with old password provided
d2fa --password oldpassword vault change-password
# (Will prompt for new password interactively)
```

**Notes:**
- Requires both old and new passwords
- New password strength is validated
- If new password is weak and `reject_weak_passwords = true`, operation is rejected
- Requires interactive mode

### `code` - Generate TOTP Code

Generates and displays the current TOTP code for an entry.

`NAME` is matched case-sensitively: an exact account name takes precedence over
issuer matches. If there is no exact account name, a unique issuer is accepted.
Multiple exact account names or multiple fallback issuers produce an
`Ambiguous entry` error (exit status 6). No code is generated or copied in that
case. For example, a different account whose issuer is `GitHub` cannot shadow
an account named `GitHub`.

```bash
d2fa code [OPTIONS] NAME
```

**Parameters:**
- `NAME`: Issuer or account name

**Options:**
- `--copy`, `-c`: Copy code to clipboard and print
- `--copy-only`: Copy code to clipboard without printing
- `--json`: Output in JSON format
- `--raw`: Output only the TOTP code
- `--quiet`: Suppress normal output

**Notes:**
- Clipboard is always opt-in; default behavior prints to terminal only
- `--copy` and `--copy-only` are mutually exclusive
- `--json` conflicts with `--raw`, `--quiet`, `--copy`, and `--copy-only`
- `--raw` conflicts with `--json`, `--quiet`, `--copy`, and `--copy-only`
- `--quiet` conflicts with `--json` and `--raw`
- Clipboard is shared system-wide; Desktop-2FA never clears it automatically

### Clipboard Requirements

Desktop-2FA uses the pyperclip library for clipboard operations. On Linux, pyperclip requires one of the following tools to be installed:

- xclip
- xsel
- wl-clipboard (for Wayland)

macOS and Windows work out of the box without additional dependencies.

If none of these tools are installed on Linux, clipboard operations will fail and desktop-2fa will fall back to printing the code normally.

### Early Textual UI Prototype

The optional Textual interface is at an **early prototype stage**. It displays
vault entries and lets you generate or copy a TOTP code for the selected entry:

```bash
# Use the default vault
d2fa ui

# Select a vault and read its password from a file
d2fa --vault ./development-vault --password-file ~/.vault_pass ui
```

When no password option is supplied, the CLI prompts for the vault password.
The interface does not provide entry-management commands or create a missing
vault; initialize one with `d2fa vault init` before launching the UI.

**Examples:**
```bash
# Default: print to terminal
d2fa code GitHub
# Output: 123456 (valid 25s)

# Copy and print
d2fa code --copy GitHub
# Output: Copied to clipboard: 123456 (valid 25s)

# Copy only (no output)
d2fa code --copy-only GitHub
# Output: Code copied to clipboard (valid 25s)

# JSON output
d2fa code --json GitHub
# Output: {"account": "GitHub", "issuer": "GitHub", "code": "123456", "valid_for": 25}

# Raw output (code only)
d2fa code --raw GitHub
# Output: 123456

# Quiet mode (no output on success)
d2fa code --quiet GitHub
# Output: (none)
```

### Exit Codes

Desktop-2FA uses the following exit codes:

- `0`: Success
- `1`: Generic error
- `2`: Invalid password
- `3`: Entry not found
- `4`: Vault missing
- `5`: Clipboard unavailable
- `6`: Invalid flag combination, ambiguous entry selection or invalid provisioning URI

### JSON Error Format

When using `--json` mode, errors are returned as JSON objects:

```json
{
  "error": "<error_code>",
  "message": "<human-readable message>"
}
```

**Error codes:**
- `invalid_password`: Invalid vault password
- `entry_not_found`: Entry not found
- `entry_ambiguous`: Multiple entries match at the selected lookup tier
- `vault_missing`: No vault found
- `vault_io_error`: Failed to access vault file
- `permission_denied`: Cannot access vault directory
- `corrupted_vault`: Vault file is corrupted
- `unsupported_format`: Vault file format is unsupported
- `clipboard_unavailable`: Clipboard not available on this system

### `remove` - Remove Entry

Deletes a TOTP entry from the vault.

Selection uses the same exact-account-name priority and unique-issuer fallback
as `code`. Ambiguous selection exits with status 6 and leaves the vault file
unchanged. Existing duplicate names are not automatically repaired.

```bash
d2fa remove NAME
```

**Parameters:**
- `NAME`: Issuer or account name to remove

**Examples:**
```bash
d2fa remove GitHub
# Output: Removed entry: GitHub

d2fa remove "AWS:root"
```

### `rename` - Rename Entry

Changes the name and issuer of an existing entry. Both the unique identifier (account name) and display label (issuer) are updated to the new name.

```bash
d2fa rename OLD_NAME NEW_NAME [--index N]
```

**Parameters:**
- `OLD_NAME`: Current issuer/account name
- `NEW_NAME`: New name (will update both account name and issuer)
- `--index N`: Select the one-based entry number displayed by `d2fa list --indices`

**Examples:**
```bash
d2fa rename GitHub GitHub-work
# Output: Renamed 'GitHub' → 'GitHub-work'
```

Rename first matches the exact account name, then falls back to the issuer if
no account name matches. Ambiguity without `--index` refuses the change.
With `--index`, the selected entry must match `OLD_NAME` at that same lookup
tier; an unrelated entry number is rejected. Matching is case-sensitive.

The new account name must not belong to any other entry, even when an index
is supplied. A name that only matches another entry's issuer is allowed:
subsequent lookups still prefer the exact account name. Renaming a uniquely
named entry to its own name is allowed and updates its issuer to that name;
a self-rename that retains a duplicated account name is rejected.

Occupied destinations, ambiguity and out-of-range or mismatched indices exit
with status 6 and leave the vault file unchanged. Non-integer CLI arguments
are usage errors (status 2). `Vault.rename_entry(old, new, index=N)` and
the public rename helper apply the same rules. Python callers receive
`EntryRenameError` for invalid indices or occupied destinations, and
`AmbiguousEntry` for unresolved ambiguity (both are `ValueError` subclasses).
The previously unimplemented `Vault.rename_entry()` now performs the rename.

### `export` - Export Vault

Exports the vault to a file (for backup or transfer).

```bash
d2fa export FILENAME
```

**Parameters:**
- `FILENAME`: Path where to save the exported vault

**Examples:**
```bash
d2fa export backup.bin
# Output: Exported vault to: backup.bin

d2fa export ~/vault_backup.bin
```

### `import` - Import Vault

Imports a vault from a file.

```bash
d2fa import SOURCE_FILE [--force]
```

**Parameters:**
- `SOURCE_FILE`: Path to the vault file to import

**Options:**
- `--force`: Overwrite existing vault

**Examples:**
```bash
d2fa import backup.bin
# Output: Vault imported from backup.bin

# Overwrite existing vault
d2fa import new_vault.bin --force
```

### `backup` - Create Backup

Creates an automatic backup of the current vault.

```bash
d2fa backup
```

**Examples:**
```bash
d2fa backup
# Output: Backup created: /home/user/.desktop-2fa/vault.backup.bin

# If backup already exists:
# Output: Backup created: /home/user/.desktop-2fa/vault.backup-1.bin
```

## Password Management

### Password Sources

Desktop-2FA supports multiple ways to provide passwords:

1. **Interactive Prompt** (default in terminal):
   ```bash
   d2fa list
   # Enter vault password:
   ```

2. **Command Line Option**:
   ```bash
   d2fa --password mypassword list
   ```

3. **Password File**:
   ```bash
   echo "mypassword" > ~/.vault_pass
   d2fa --password-file ~/.vault_pass list
   ```


### Password Strength Enforcement

Desktop-2FA uses **zxcvbn** to evaluate password strength when creating or changing vault passwords. Configure via `~/.config/d2fa/config.toml`:

```toml
[security]
# Reject weak passwords (password score < 3)
reject_weak_passwords = false

# Warn when unlocking vault if password is weak
warn_on_weak_existing_passwords = false

# Legacy option (recognized but uses zxcvbn scoring)
min_password_entropy = 60
```

**zxcvbn Scoring:**
- **Score 0-2 (Weak)**: Easily guessable passwords like "password", "123456", "qwerty"
- **Score 3-4 (Strong)**: Resilient passwords like "Battery-Horse-Staple", "Mountain@River2024"

**Configuration Options:**
- **reject_weak_passwords**: If true, weak passwords are rejected immediately; if false (default), user is warned and can confirm
- **warn_on_weak_existing_passwords**: If true, warns when unlocking vault with weak password (non-blocking)
- **min_password_entropy**: Legacy option - values are mapped to zxcvbn score thresholds (60+ bits ≈ score 3)

**Bypass:** Use `--allow-weak-passwords` or set `D2FA_ALLOW_WEAK_PASSWORDS=1` to skip strength checks.

### Password Validation Rules

Desktop-2FA enforces the following password validation rules:

1. **Empty Passwords**: Empty passwords are immediately rejected with error: `Password cannot be empty.`
   - This applies to all password input methods (interactive, `--password`, `--password-file`)
   - No entropy calculation is performed on empty passwords
   - No confirmation prompt is shown for empty passwords
   - Vault creation is blocked

2. **Password Confirmation**: When creating a new vault, you must enter the password twice for confirmation
   - If passwords don't match, you'll be prompted to try again

3. **Password Strength**: Weak passwords trigger a warning or rejection based on configuration

### Security Notes

- Passwords are never stored or logged (except temporarily in memory)
- Use strong, unique passwords
- Consider using password managers for vault passwords
- The vault is encrypted with AES-256-GCM + Argon2
- The vault always requires the real master password for decryption
- Password authentication is mandated for every vault access

## Configuration

Desktop-2FA can be configured via `~/.config/d2fa/config.toml`:

```toml
[security]
# Reject weak passwords (zxcvbn score < 3)
reject_weak_passwords = false

# Warn when unlocking vault with weak password
warn_on_weak_existing_passwords = false

# Legacy entropy option (mapped to zxcvbn score)
min_password_entropy = 60
```

### Configuration Options

- **reject_weak_passwords** (default: false): Whether to reject weak passwords (true) or warn and allow (false)
- **warn_on_weak_existing_passwords** (default: false): Whether to warn when unlocking vault with weak password
- **min_password_entropy** (default: 60): Legacy option - minimum password entropy in bits (mapped to zxcvbn score ≥ 3)

The config file is optional - defaults are used if the file doesn't exist.

## Vault File Location

By default, the vault is stored at:
- Linux/macOS: `~/.desktop-2fa/vault`
- Windows: `C:\Users\<username>\.desktop-2fa\vault`

The vault file is automatically created on first use. See [Selecting the Vault
File](#selecting-the-vault-file) for custom paths and environment overrides.
For safety, vault files must be regular files no larger than 10 MiB.

## Error Handling

### Common Errors

**"Invalid vault password"**
- The provided password is incorrect
- Check for typos or use the correct password source

**"Vault file format is unsupported"**
- You're trying to use a vault created with desktop-2fa < 0.6.0
- Create a new vault with `d2fa init-vault`

**"Invalid secret: not valid Base32"**
- The TOTP secret contains invalid characters
- Verify the secret from your service provider
- Example of valid Base32: ABCDEFGHIJKL2345

**"Entry 'NAME' not found"**
- The specified entry doesn't exist
- Use `d2fa list` to see available entries

**"Password too weak (score X < Y)"**
- The vault password doesn't meet strength requirements (zxcvbn score is weak)
- Examples of weak passwords: "password", "123456", "admin2024"
- Either strengthen the password or use `--allow-weak-passwords`
- Configure requirements in `~/.config/d2fa/config.toml`

**"Password cannot be empty."**
- Empty passwords are not allowed
- Provide a non-empty password

**"Passwords do not match"**
- Confirmation password doesn't match the initial password
- Re-run the command and ensure both passwords are identical

**"Error: Cannot specify both --password and --password-file"**
- You provided both password options simultaneously
- Use only one: either `--password` or `--password-file`

**"Error: Password not provided and not running in interactive mode"**
- No password source available in non-interactive environment
- Provide `--password` or `--password-file`, or run in a terminal

**"Error: Cannot access vault directory (permission denied)"**
- You do not have permission to read/write the vault location
- Check file permissions for `~/.desktop-2fa/`
- On Linux/macOS: `chmod 700 ~/.desktop-2fa`
- On Windows: Check folder properties → Security → Permissions


## Advanced Usage

### Batch Operations

```bash
# Add multiple entries
d2fa add GitHub GitHub JBSWY3DPEHPK3PXP
d2fa add AWS Amazon ABCDEFGHIJKLMNOP
d2fa add Google Google QRSTUVWXYZ123456

# List all
d2fa list

# Generate codes for multiple services
d2fa code GitHub
d2fa code AWS
d2fa code Google
```

### Backup Strategy

```bash
# Regular backup
d2fa backup

# Export to external location
d2fa export ~/Documents/vault-$(date +%Y%m%d).bin

# Import from backup
d2fa import ~/Documents/vault-20231201.bin --force
```

### Migration Between Machines

```bash
# On source machine
d2fa export transfer.bin

# Transfer transfer.bin to new machine

# On destination machine
d2fa import transfer.bin
```

## Troubleshooting

### Vault Not Found

If you get "No vault found" errors:

```bash
# Initialize new vault
d2fa vault init

# Or check vault location
ls -la ~/.desktop-2fa/
```

### Permission Issues

Ensure you have read/write permissions for `~/.desktop-2fa/`

```bash
mkdir -p ~/.desktop-2fa
chmod 700 ~/.desktop-2fa
```

### Forgotten Password

**Important:** There is no way to recover a forgotten password. The vault encryption is designed to be unbreakable without the correct password.

If you forget your password:
1. Restore from a backup (if available)
2. Re-export tokens from your service providers
3. Create a new vault

### Version Compatibility

- Vaults created with desktop-2fa 0.6.0+ are designed to remain compatible with
  newer releases
- Older vaults (pre-0.6.0) are not compatible and must be recreated

Although newer releases are designed to remain compatible with vaults from
0.6.0 onward, we strongly recommend creating and securely storing an encrypted
backup before every upgrade. Compatibility is not a substitute for a backup:
an upgrade can still be interrupted or affected by local system issues.
Create a backup with:

```bash
d2fa backup
```

### Duplicate Names in Vault

If you have a vault created with an older version of desktop-2fa that allowed duplicate names, you may see a warning when loading the vault:

```
Warning: Your vault contains multiple entries with the same name: "GitHub", "AWS".
This was allowed in older versions. Run 'd2fa list --indices', then 'd2fa rename OLD NEW --index N' to select one entry.
```

**Resolution:**
Back up the selected vault and display its current entry numbers. For example,
if `./legacy-vault.bin` contains three entries named `GitHub` at indices 1–3:

```bash
d2fa --vault ./legacy-vault.bin backup
d2fa --vault ./legacy-vault.bin list --indices
# [1] 'GitHub' ('personal')
# [2] 'GitHub' ('work')
# [3] 'GitHub' ('test')

d2fa --vault ./legacy-vault.bin rename GitHub GitHub-personal --index 1
d2fa --vault ./legacy-vault.bin rename GitHub GitHub-work --index 2
d2fa --vault ./legacy-vault.bin rename GitHub GitHub-test --index 3
d2fa --vault ./legacy-vault.bin list --indices
```

Rename keeps list order, secret bytes, algorithm, digits and period; only the
selected entry's account name and issuer change. After all duplicate names
are repaired, the warning disappears. Loading and listing do not migrate data.

Indices refer to the current full list and are not stored identifiers. List
again after additions or removals, check `OLD_NAME` and the selected number,
and avoid concurrent edits during repair. An index is range-checked and must
match the old name, but it cannot detect another process reordering identical
duplicates between commands. The default `list` output is unchanged; the
optional numbered view escapes line breaks in labels and shows no secrets.

## Contact

For questions or support, contact us at contact@desktop-2fa.org

## Command Reference

```bash
d2fa --help                    # Show general help
d2fa COMMAND --help           # Show help for specific command
d2fa --version                # Show version
d2fa                         # Show version (no args)
d2fa vault path               # Show the selected vault path
d2fa ui                       # Launch the early Textual UI prototype
```

## Security Best Practices

1. **Use strong passwords** for your vault (zxcvbn score 3-4 recommended)
   - Examples of strong passwords: "Battery-Horse-Staple", "Mountain@River2024"
   - Avoid common words, sequential numbers, keyboard patterns
2. **Keep backups** in secure locations
3. **Regularly update** desktop-2fa
4. **Verify secrets** when adding entries
5. **Use password files** for automation (with proper file permissions)
6. **Keep vault file secure** - don't share or store in insecure locations
7. **Stateless design** - every command requires explicit password authentication
8. **Use `--allow-weak-passwords`** only when necessary (testing, legacy systems)
9. **Configure password policies** in `~/.config/d2fa/config.toml`:
   - Set `reject_weak_passwords = true` for strict enforcement
   - Set `warn_on_weak_existing_passwords = true` to check existing vault passwords
10. **Test password strength** - run `d2fa vault unlock` to verify your password strength

## Support

For issues and questions:
- Check this manual first
- Review error messages carefully
- Ensure you're using the latest version
- File issues on GitHub if needed

---

*This manual covers desktop-2fa version 0.9.0*
