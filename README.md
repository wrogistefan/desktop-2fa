# 🛡️ Desktop-2FA

A secure, offline two-factor authentication (2FA) manager for desktop environments. Built with Python, featuring strong encryption and no cloud dependencies.

🌐 **Landing Page**: [desktop-2fa.org](https://desktop-2fa.org/)

![PyPI - Downloads](https://img.shields.io/pypi/dm/desktop-2fa)
[![PyPI version](https://img.shields.io/pypi/v/desktop-2fa.svg)](https://pypi.org/project/desktop-2fa/)
![Python versions](https://img.shields.io/pypi/pyversions/desktop-2fa.svg)
![License](https://img.shields.io/github/license/wrogistefan/desktop-2fa)
![Build](https://github.com/wrogistefan/desktop-2fa/actions/workflows/ci.yml/badge.svg)
[![codecov](https://codecov.io/gh/wrogistefan/desktop-2fa/branch/main/graph/badge.svg)](https://codecov.io/gh/wrogistefan/desktop-2fa)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔐 **Vault Security** | AES-256-GCM encryption with Argon2id key derivation |
| ⏱️ **TOTP Generation** | RFC 6238 compliant code generation |
| 💻 **Full CLI** | Complete command-line interface for managing tokens |
| 📋 **Clipboard Support** | Automatic copying of TOTP codes to clipboard |
| 🔓 **Stateless Design** | Vault contents require authentication; no long-lived sessions |
| 🛡️ **Password Policy** | Configurable password strength enforcement with zxcvbn |
| 🧪 **Well Tested** | 302 tests passing with comprehensive coverage |
| 📖 **Security Model** | Detailed threat analysis and cryptographic design documentation |
| 🖥️ **Textual UI** | Prototype interface for generating and copying TOTP codes |

---

## 📸 Screenshots

![Add entry interactively](https://raw.githubusercontent.com/wrogistefan/desktop-2fa/main/assets/screenshots/add_interactive.png)
*Adding a new TOTP entry interactively*

![Code generation](https://raw.githubusercontent.com/wrogistefan/desktop-2fa/main/assets/screenshots/codegen_ss.png)
*Generating a TOTP code for an entry*

![Rename and duplicate error](https://raw.githubusercontent.com/wrogistefan/desktop-2fa/main/assets/screenshots/rename_add_duplicate.png)
*Renaming an entry with duplicate detection*

![Version and list](https://raw.githubusercontent.com/wrogistefan/desktop-2fa/main/assets/screenshots/version_list_ss.png)
*Viewing version info and listing all entries*

---

## 🚀 Quick Start

### Installation

```bash
pip install desktop-2fa
```

Verify installation:

```bash
python -c "import desktop_2fa; print(desktop_2fa.__version__)"
# Output: 0.8.2
```

### Basic Usage

```bash
# Initialize a new vault
d2fa vault init

# Add a new TOTP token
d2fa add GitHub GitHub JBSWY3DPEHPK3PXP

# List all entries
d2fa list

# Generate a code
d2fa code GitHub
```

The vault is stored by default at `~/.desktop-2fa/vault`. Select a different
file for any command with the global `--vault` option, or set
`DESKTOP_2FA_VAULT` to choose one by default. An explicit `--vault` takes
precedence over the environment variable; without either, the default remains
`~/.desktop-2fa/vault`.

```bash
# Use a separate vault for this command
d2fa --vault ./development-vault list

# Show the currently selected vault path
d2fa --vault ./development-vault vault path

# Launch the Textual prototype with that vault
d2fa --vault ./development-vault ui
```

The Textual UI prompts for the vault password unless one is supplied with
`--password` or `--password-file`. It supports listing entries, generating
codes, and copying codes to the clipboard.

### Non-Interactive Usage

```bash
# Provide password via command line
d2fa --password mypassphrase add GitHub GitHub JBSWY3DPEHPK3PXP

# Provide password via file
d2fa --password-file /path/to/passphrase.txt add GitHub GitHub JBSWY3DPEHPK3PXP
```

---

## 📁 Vault Lifecycle

The vault is an encrypted storage file located by default at
`~/.desktop-2fa/vault`; use `--vault` or `DESKTOP_2FA_VAULT` to select another
path. Vault files must be regular files no larger than 10 MiB.

### Vault Creation

When a CLI command that creates or updates entries requires a vault and none exists:

1. The CLI prompts for a new password (interactive mode) or requires `--password`/`--password-file` (non-interactive mode)
2. An empty encrypted vault is created
3. **A confirmation message is always printed:** `Vault created at <path>`

The Textual UI does not create a missing vault; it displays the vault-loading
error instead.

### Vault Loading

When a command requires a vault and it exists:

1. The CLI prompts for the existing password (interactive mode) or requires credentials (non-interactive mode)
2. The vault is decrypted and loaded
3. If the password is invalid, the CLI exits with `typer.Exit(1)`

### Duplicate Entry Handling

The `rename` command enforces deterministic behavior when multiple entries match the target name:

- If **multiple entries** match the provided name (issuer or account_name), the rename is **aborted**
- Error message: `Error: Multiple entries named '<name>' exist. Operation aborted. Resolve duplicates first.`
- No entry is renamed in this case
- This check occurs **before** any mutation

---

## 📖 CLI Commands

### Core Commands

| Command | Description |
|---------|-------------|
| `d2fa add <name> <issuer> <secret>` | Add a new TOTP entry |
| `d2fa list` | List all stored TOTP entries |
| `d2fa rename <old> <new>` | Rename an entry |
| `d2fa remove <name>` | Remove an entry |
| `d2fa code <name> [--copy\|--copy-only]` | Generate TOTP code with clipboard copy options |

### Vault Management

| Command | Description |
|---------|-------------|
| `d2fa vault init [--force]` | Initialize a new vault (`d2fa init-vault` is an alias) |
| `d2fa vault unlock` | Open vault with weak password warning (if configured) |
| `d2fa vault change-password` | Change the vault password |
| `d2fa vault path` | Show the currently selected vault path |
| `d2fa backup` | Create an encrypted backup of the vault |
| `d2fa export <path>` | Export vault to file |
| `d2fa import <path> [--force]` | Import vault from file |
| `d2fa ui` | Launch the Textual prototype interface |

### Global Options

| Option | Description |
|--------|-------------|
| `--version` | Show the installed version |
| `--password <pwd>` | Provide vault password directly |
| `--password-file <path>` | Read vault password from file |
| `--vault <path>` | Select the vault file; place before the command |
| `--allow-weak-passwords` | Allow weak passwords |
| `--help` | Show command help |

The `--vault` option takes precedence over `DESKTOP_2FA_VAULT`. When neither
is provided, Desktop-2FA uses `~/.desktop-2fa/vault`. The `code` command also
supports `--json`, `--raw`, `--quiet`, `--copy`, and `--copy-only`; `--force`
is available on vault initialization and import commands.

---

## 🔒 Security

The vault uses:
- **AES-256-GCM** for authenticated encryption
- **Argon2id** for key derivation (time_cost=4, memory_cost=128MiB, parallelism=2)
- **zxcvbn** for password strength evaluation
- **Versioned header** for forward compatibility

Every command that accesses vault contents requires password authentication.
Path and version queries do not access vault contents. No session-based access.

### Password Strength Evaluation

Desktop-2FA uses **zxcvbn** to evaluate password strength when creating or changing vault passwords:

- **Score 0-2 (Weak)**: Easily guessable passwords (e.g., "password123")
- **Score 3-4 (Strong)**: Resistant to common attacks (recommended)

**Examples:**
- ❌ Weak: `password`, `123456`, `qwerty`, `admin2024`
- ✅ Strong: `Battery-Horse-Staple-Correct`, `Mountain@River*2024`, `MySecureVault#42`

**Configuration** (`~/.config/d2fa/config.toml`):

```toml
[security]
# Require strong passwords (score >= 3)
reject_weak_passwords = false  # warn but allow | true: reject weak passwords
```

When `reject_weak_passwords = false`:
- Weak passwords trigger a yellow warning
- User is prompted to confirm continuation
- Password acceptance is non-blocking

When `reject_weak_passwords = true`:
- Weak passwords are rejected immediately
- Command exits with error
- User must choose a stronger password

**Backward Compatibility:**
If you have `min_password_entropy` set in your config (legacy option), it is recognized and treated as equivalent to requiring zxcvbn score >= 3.

### Security Hardening
Version 0.8.2 maintains previous security hardening and adds bounded vault loading and atomic saves:
- Empty passwords are immediately rejected with a clear error message
- Permission errors are distinguished from missing vault files
- Vault loading accepts only regular files and reads at most 10 MiB
- Vault saves use unique temporary files and atomic replacement
- No Python stack traces are shown to users
- User-friendly error messages for filesystem permission issues
- Modular design separates CLI and core cryptographic components for enhanced security boundaries
- zxcvbn-based password strength evaluation


---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [User Manual](docs/user_manual.md) | Complete usage guide |
| [Security Model](docs/SECURITY.md) | Detailed threat analysis and cryptographic design |
| [CLI UX Specification](docs/ux.md) | UX contract and behavior |
| [Cryptography](docs/crypto.md) | Security implementation details |

---

## 🧪 Testing

```bash
pytest tests/              # Run all tests
pytest --cov=src/desktop_2fa  # Run with coverage
```

---

## 🏗️ Project Structure

```
src/desktop_2fa/
├── app/           # Application components
├── cli/           # Command-line interface
├── crypto/        # Encryption utilities
├── totp/          # TOTP generation
├── ui_textual/    # Textual prototype interface
├── vault/         # Vault management
└── utils/         # Utilities
```

---

## 📄 License

Apache License 2.0. See [LICENSE](LICENSE) file.

---

## 👤 Author

Łukasz Perek

---

## 🏆 Sponsorship

desktop‑2fa is supported through the Kilo OSS Sponsorship Program.

---

## 📧 Contact

For questions or support, contact us at contact@desktop-2fa.org

---

## 💖 Support the Project

Desktop‑2FA is an independent open‑source tool built with a focus on autonomy, transparency, and offline security.
If you find it useful and want to support ongoing development, you can do so through the platforms below:

- **Ko‑fi**: https://ko-fi.com/lukaszperek
- **Buy Me a Coffee**: https://buymeacoffee.com/lukaszperek
- **AirTM**: https://airtm.me/lukper
