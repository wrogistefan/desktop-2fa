# 🛡️ Desktop-2FA
![PyPI - Downloads](https://img.shields.io/pypi/dm/desktop-2fa)
[![PyPI version](https://img.shields.io/pypi/v/desktop-2fa.svg)](https://pypi.org/project/desktop-2fa/)
![Python versions](https://img.shields.io/pypi/pyversions/desktop-2fa.svg)
![License](https://img.shields.io/github/license/wrogistefan/desktop-2fa)
![Build](https://github.com/wrogistefan/desktop-2fa/actions/workflows/ci.yml/badge.svg)
[![codecov](https://codecov.io/gh/wrogistefan/desktop-2fa/branch/main/graph/badge.svg)](https://codecov.io/gh/wrogistefan/desktop-2fa)
[![Live site](https://img.shields.io/badge/live-desktop--2fa-blue?style=for-the-badge)](https://desktop-2fa.lukasz-perek.workers.dev/)

## ⚠️ IMPORTANT NOTICE — Vault Format Change (0.6.0)

Starting with desktop‑2fa 0.6.0, the vault file format has been fully audited and stabilized as part of the Vault Security Audit (Phases 1–5).

This audit introduced a strict, versioned vault header and hardened cryptographic parameters.

As a result:

Vaults created with versions prior to 0.6.0 are not compatible with 0.6.0+.

Older vaults did not include:

- a version field in the header,
- the finalized magic header (D2FA),
- the audited Argon2id parameters,
- the stable ciphertext layout introduced after the audit.

Because these fields are now required for safe parsing and forward compatibility, vaults created before the audit cannot be imported by current versions of the application.

This is intentional and was required to guarantee:

- deterministic parsing rules,
- safe rejection of malformed or ambiguous vaults,
- future‑proofing for format evolution,
- cryptographic correctness validated in the audit.

### What this means for users

If your vault was created with 0.5.6 or earlier, it will be rejected as "unsupported format".

You will need to initialize a new vault using `d2fa init-vault`.

All vaults created with 0.6.0 and later include a versioned header and will remain compatible with future releases.

### Why no automatic migration?

The pre‑audit vaults lacked the metadata required to safely migrate them:

- no version field → impossible to reliably detect layout,
- inconsistent Argon2id parameters → unsafe to reinterpret,
- no stable header → cannot distinguish valid vaults from corrupted files,
- ciphertext structure changed during the audit.

Attempting to "guess" the format would introduce ambiguity and weaken the security guarantees established by the audit.

### Going forward

From 0.6.0 onward:

- every vault includes a versioned header,
- the format is stable and forward‑compatible,
- future changes will be handled through explicit version bumps,
- no further breaking changes are expected.

This ensures that vaults created today will remain readable in all future versions.

---

A secure, offline two-factor authentication (2FA) manager designed for desktop environments. Built with a modular architecture in Python, featuring strong encryption and no cloud dependencies.

🌐 **Landing Page**: Visit [desktop-2fa.lukasz-perek.workers.dev](https://desktop-2fa.lukasz-perek.workers.dev/)

## Features

- **🔐 Vault**: Storage using AES-256-GCM encryption with Argon2 key derivation.
- **⏱️ TOTP Generation**: RFC 6238 compliant Time-based One-Time Password (TOTP) generation.
- **📋 Clipboard Integration**: Automatic copying of generated codes for convenience.
- **🖥️ Desktop-First Design**: Native desktop application with no internet connectivity required.
- **💻 Command-Line Interface**: Full CLI for managing 2FA tokens without a GUI.
- **🔓 Stateless Design**: Every command requires explicit password authentication.
- **🛡️ Password Strength Enforcement**: Configurable entropy checking with warnings/rejection.
- **🧠 Modular Architecture**: Clean separation of concerns across crypto, vault, UI, and utility modules.
- **🧪 Comprehensive Testing**: Full test coverage using pytest with security regression tests.
- **🚀 Future-Proof**: Designed for easy migration to Rust for enhanced performance.

## 🚀 What's New in v0.6.3

- **Critical Security Fix**: Removed password storage from unlock file - vault always requires real master password for decryption.
- **Interactive CLI Improvements**: Visible secret input in `add` command, Rich-formatted cyan issuer prompts.
- **Password Strength Enforcement**: Configurable entropy checking via `~/.config/d2fa/config.toml` with warnings/rejection.
- **CLI Bypass Options**: `--allow-weak-passwords` flag and `D2FA_ALLOW_WEAK_PASSWORDS` env var for testing/legacy scenarios.
- **Enhanced Security Testing**: Added regression tests ensuring unlock never bypasses password requirements.

### Previous v0.6.0+ Features
- **Security Audit Completion**: Comprehensive vault security audit (Phases 1–5) with hardened Argon2id parameters.
- **Vault Format Stabilization**: Strict, versioned vault header (D2FA v1) for forward compatibility.
- **Breaking Change**: Vaults created prior to 0.6.0 are not compatible; initialize new vaults with `d2fa init-vault`.
- **Enhanced Testing**: 31+ deterministic tests covering security, UX, and integration scenarios.
- **CI Compliance**: All checks pass (Ruff, Black, MyPy, full test suite).

##  Vault Storage

All secrets are stored in a local vault using:

- AES-GCM encryption
- Argon2 key derivation
- Binary format (`vault.bin`) in `~/.desktop-2fa/`

Vault is automatically backed up as `vault.backup.bin` on each save.

### Security Model

The vault encryption is backed by a user-provided passphrase for strong security.

- The vault is encrypted using AES-256-GCM with authenticated encryption.
- The encryption key is derived using Argon2 from the user-provided passphrase combined with a per-vault random salt.
- The salt is stored securely alongside the ciphertext in the vault file.
- A passphrase is mandatory for vault decryption and must be provided via CLI options or interactive prompt.
- Password strength can be enforced via configuration with entropy checking.
- Every command requires explicit password authentication - no session-based access.

**Security Implications:**
This implementation provides robust protection against unauthorized access. An attacker with access to the vault file cannot decrypt it without the passphrase, offering strong cryptographic security. Every command requires explicit password authentication, ensuring no session-based vulnerabilities.

**Important Note:**
While the vault is encrypted, it is important to understand that the security of the vault depends entirely on the strength of the user-provided passphrase. Additionally, the vault is stored locally on the same device, which means that if the device is compromised, the vault could be accessed. For maximum security, consider using a dedicated device for storing sensitive information.

## CLI UX Specification

CLI behavior is defined by an explicit UX contract that ensures consistent and predictable interactions. The vault lifecycle and first-use behavior are thoroughly documented to guide user expectations and system responses. This UX specification serves as the foundation for future refactors and GUI work, maintaining alignment across all interfaces.

See [docs/ux.md](docs/ux.md) for details.

## Installation

### From PyPI (Recommended)

```bash
pip install desktop-2fa
```

Verify installation:

```bash
python -c "import desktop_2fa; print(desktop_2fa.__version__)"
```

Expected output: `0.6.6`

### From Source

Clone the repository and install dependencies:

```bash
git clone https://github.com/wrogistefan/desktop-2fa.git
cd desktop-2fa
pip install -e .
```

## Supported Python Versions

Python 3.11, 3.12, 3.13

## 🔧 Upgrade Guide (v0.4.x → v0.5.0)

If upgrading from v0.4.x:

1. Export your existing vault: `desktop-2fa export backup.json`
2. Upgrade the package: `pip install --upgrade desktop-2fa`
3. Import the vault: `desktop-2fa import backup.json`

Note: The vault format has changed; export/import ensures compatibility.

## Integrity

This release is signed with a GPG key to ensure authenticity and tamper-resistance.

## Usage

Launch the application:

```bash
desktop-2fa
```

### Adding Tokens

Use the UI to add new TOTP tokens by providing the secret key, issuer, and other details.

### Generating Codes

The application will automatically generate and display TOTP codes based on the current time. Codes are copied to the clipboard for easy use.

## 🧪 CLI Usage

```bash
# Show version
desktop-2fa --version
# or just run without args
desktop-2fa

# Add interactively (prompts for issuer and secret)
desktop-2fa add
# Add with arguments
desktop-2fa add GitHub JBSWY3DPEHPK3PXP

desktop-2fa list
desktop-2fa code GitHub
desktop-2fa rename GitHub GitHub2
desktop-2fa remove GitHub2
desktop-2fa export vault.json
desktop-2fa import vault.json
desktop-2fa backup
desktop-2fa init-vault

# Provide passphrase via command line option
desktop-2fa --password mypassphrase add GitHub JBSWY3DPEHPK3PXP

# Provide passphrase via file
desktop-2fa --password-file /path/to/passphrase.txt add GitHub JBSWY3DPEHPK3PXP

# Bypass password strength checks
desktop-2fa --allow-weak-passwords add GitHub JBSWY3DPEHPK3PXP

# Interactive mode (prompts for passphrase if not provided)
desktop-2fa add GitHub JBSWY3DPEHPK3PXP

# Import from another vault file
desktop-2fa import backup.bin
```

**Note**: The `export` and `import` commands work with JSON files for data interchange, while the vault is stored internally as an encrypted binary file. Use `export` to create a portable backup and `import` to restore from a JSON file.

For detailed help on any command, use `desktop-2fa <command> --help` or `desktop-2fa --help` for general help.

## Project Structure

```
src/desktop_2fa/
├── app/
│   ├── __init__.py
│   ├── clipboard.py    # Clipboard handling utilities
│   ├── config.py       # Application configuration
│   └── main.py         # Application entry point
├── cli/
│   ├── __init__.py
│   ├── commands.py     # CLI command implementations
│   ├── helpers.py      # CLI helper functions
│   ├── importers.py    # Import utilities for various formats
│   ├── main.py         # CLI entry point with Typer app
│   └── requirements.txt # CLI-specific dependencies
├── crypto/
│   ├── __init__.py
│   ├── aesgcm.py       # AES-GCM encryption utilities
│   └── argon2.py       # Argon2 key derivation
├── totp/
│   ├── __init__.py
│   └── generator.py    # RFC 6238 TOTP generation
├── ui/
│   ├── __init__.py
│   ├── add_token_dialog.py  # Dialog for adding tokens
│   ├── main_window.py       # Main UI window
│   └── resources/
│       └── __init__.py
├── utils/
│   ├── __init__.py
│   └── time.py         # Time-related utilities
├── vault/
│   ├── __init__.py
│   ├── models.py       # Vault data models
│   └── vault.py        # Vault management
└── __init__.py         # Package initialization
tests/
├── __init__.py
├── test_cli.py         # CLI tests
├── test_commands.py    # CLI command tests
├── test_crypto.py      # Crypto tests
├── test_helpers.py     # CLI helper tests
├── test_migration.py   # Migration tests
├── test_totp.py        # TOTP tests
├── test_vault_crypto.py # Vault crypto tests
└── test_vault.py       # Vault tests
```

## Testing

Run the test suite using pytest:

```bash
pytest tests/
```

## 🧠 Developer Notes

This version uses Pydantic v2 for data modeling:

- `@field_validator`: Custom validation for fields like Base32 secrets.
- `model_dump_json()`: Serialize models to JSON.
- `model_validate_json()`: Deserialize and validate JSON data.

## Vault Format

The vault stores encrypted data in a binary format saved as `vault.bin` in `~/.desktop-2fa/`. The vault uses AES-GCM encryption with Argon2 key derivation. Automatic backups are created as `vault.backup.bin` on each save.

For export/import operations, data can be converted to/from JSON format with the following structure:

```json
{
  "version": 1,
  "entries": [
    {
      "issuer": "GitHub",
      "account_name": "GitHub",
      "secret": "JBSWY3DPEHPK3PXP",
      "digits": 6,
      "period": 30,
      "algorithm": "SHA1"
    }
  ]
}
```

## Vault initialization design notes

The vault file is created automatically on first use.

Historically, the application assumed the vault file already existed, which caused
silent failures for new users when running commands such as `list` or `add`.
To address this, the vault loading logic was updated to ensure that a missing vault
file is created and persisted on first access.

This behavior is intentional and guarantees that:
- new users are never blocked by missing files
- CLI commands behave deterministically
- vault creation does not require a separate manual step

At present, vault creation is coupled to the loading process.
This is a pragmatic design choice made to restore correct functionality quickly
and safely.

Future iterations may refine this design by:
- separating vault creation from loading
- introducing clearer initialization semantics
- improving first‑use UX around password prompts

These changes are tracked as follow‑up work and do not affect the correctness
or security of the current implementation.

## 🧭 Roadmap (high‑level)
v0.3.0 — CLI ✓

v0.4.0 — Vault format v2 + migrations ✓

v0.5.0 — Pydantic vault system ✓

v0.5.5 — Security enhancements and importers ✓

v0.6.0 — Vault security audit completion & format stabilization ✓

v0.6.x — Rust core (pyo3)

v1.0.0 — Stable release

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests on GitHub.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

## Author

Łukasz Perek

## ❤️ Support the Project

**Desktop-2FA** is fully open-source and free to use.

If you'd like to support its development, you can do so here:

- **Ko-fi**: [https://ko-fi.com/lukaszperek](https://ko-fi.com/lukaszperek)
- **Buy Me a Coffee**: [https://buymeacoffee.com/lukaszperek](https://buymeacoffee.com/lukaszperek)

[![Ko-fi](https://img.shields.io/badge/Ko--fi-support-blue?logo=ko-fi&style=flat-square)](https://ko-fi.com/lukaszperek)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-yellow?logo=buy-me-a-coffee&style=flat-square)](https://buymeacoffee.com/lukaszperek)

Your support helps keep the project maintained, secure, and evolving.