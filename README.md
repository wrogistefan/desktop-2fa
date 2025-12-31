# 🛡️ Desktop-2FA
![PyPI - Downloads](https://img.shields.io/pypi/dm/desktop-2fa)
[![PyPI version](https://img.shields.io/pypi/v/desktop-2fa.svg)](https://pypi.org/project/desktop-2fa/)
![Python versions](https://img.shields.io/pypi/pyversions/desktop-2fa.svg)
![License](https://img.shields.io/github/license/wrogistefan/desktop-2fa)
![Build](https://github.com/wrogistefan/desktop-2fa/actions/workflows/ci.yml/badge.svg)
[![codecov](https://codecov.io/gh/wrogistefan/desktop-2fa/branch/main/graph/badge.svg)](https://codecov.io/gh/wrogistefan/desktop-2fa)
[![Live site](https://img.shields.io/badge/live-desktop--2fa-blue?style=for-the-badge)](https://desktop-2fa.lukasz-perek.workers.dev/)


A secure, offline two-factor authentication (2FA) manager designed for desktop environments. Built with a modular architecture in Python, featuring strong encryption and no cloud dependencies.

## Features

- **🔐 Encrypted Vault**: Secure storage using AES-256-GCM encryption with Argon2 key derivation.
- **⏱️ TOTP Generation**: RFC 6238 compliant Time-based One-Time Password (TOTP) generation.
- **📋 Clipboard Integration**: Automatic copying of generated codes for convenience.
- **🖥️ Desktop-First Design**: Native desktop application with no internet connectivity required.
- **💻 Command-Line Interface**: Full CLI for managing 2FA tokens without a GUI.
- **🧠 Modular Architecture**: Clean separation of concerns across crypto, vault, UI, and utility modules.
- **🧪 Comprehensive Testing**: Full test coverage using pytest.
- **🚀 Future-Proof**: Designed for easy migration to Rust for enhanced performance.

## 🚀 What's New in v0.5.4

- **CLI Enhancements**: Added `--version` option and version display when no arguments provided.
- **Interactive Add Command**: The `add` command now prompts for issuer and secret if not provided as arguments.
- **Improved User Experience**: Better CLI usability with version information and interactive prompts.
- **Code Quality**: Achieved 100% test coverage and removed duplicate badges from README.

##  Secure Vault Storage

All secrets are stored in a local encrypted vault using:

- AES-GCM encryption
- Argon2 key derivation
- Binary format (`vault.bin`) in `~/.desktop-2fa/`

Vault is automatically backed up as `vault.backup.bin` on each save.

### Security model (current state, WIP)

Right now, the vault encryption is **not** backed by a user-provided secret.

- The vault is encrypted using AES‑GCM.
- The encryption key is derived using Argon2 from a fixed internal password plus a per‑vault random salt.
- The salt is stored alongside the ciphertext.
- There is no way for the user to set their own passphrase yet.

**Implication:**
If someone gains access to your vault file and knows how this project works, they can decrypt it. The current implementation does *not* offer strong cryptographic protection against an attacker who has a copy of the vault.

This is a known limitation and will be addressed by:

- Introducing a mandatory user passphrase for vault encryption.
- Keeping Argon2-based key derivation, but using user input as the secret.
- Updating this section with a precise, formal security model.

Until then, this project should be considered experimental and **not a replacement for established tools** like Bitwarden, KeePass, or Aegis for high‑security use cases.

## Installation

### From PyPI (Recommended)

```bash
pip install desktop-2fa
```

Verify installation:

```bash
python -c "import desktop_2fa; print(desktop_2fa.__version__)"
```

Expected output: `0.5.4`

### From Source

Clone the repository and install dependencies:

```bash
git clone https://github.com/wrogistefan/desktop-2fa.git
cd desktop-2fa
pip install -e .
```

## Supported Python Versions

Python 3.10, 3.11, 3.12, 3.13

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
│   └── main.py         # CLI entry point with Typer app
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

The vault stores encrypted data in a binary format saved as `vault.bin` in `~/.desktop-2fa/`. The vault uses AES-GCM encryption with Argon2 key derivation for maximum security. Automatic backups are created as `vault.backup.bin` on each save.

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

## 🧭 Roadmap (high‑level)
v0.3.0 — CLI ✓

v0.4.0 — Vault format v2 + migrations ✓

v0.5.0 — Pydantic vault system ✓

v0.5.4 — CLI enhancements and 100% coverage ✓

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