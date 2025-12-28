# 🛡️ Desktop-2FA
[![PyPI version](https://img.shields.io/pypi/v/desktop-2fa.svg)](https://pypi.org/project/desktop-2fa/)
![Python versions](https://img.shields.io/pypi/pyversions/desktop-2fa.svg)
![License](https://img.shields.io/github/license/wrogistefan/desktop-2fa)
![Build](https://github.com/wrogistefan/desktop-2fa/actions/workflows/ci.yml/badge.svg)
[![codecov](https://codecov.io/gh/wrogistefan/desktop-2fa/branch/main/graph/badge.svg)](https://codecov.io/gh/wrogistefan/desktop-2fa)

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

## Installation

### From PyPI (Recommended)

```bash
pip install desktop-2fa
```

Verify installation:

```bash
python -c "import desktop_2fa; print(desktop_2fa.__version__)"
```

Expected output: `0.3.0`

### From Source

Clone the repository and install dependencies:

```bash
git clone https://github.com/wrogistefan/desktop-2fa.git
cd desktop-2fa
pip install -e .
```

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

## CLI Usage

The CLI provides a comprehensive set of commands for managing your 2FA tokens:

- **List all tokens**: `desktop-2fa list`
- **Add a new token**: `desktop-2fa add <issuer> <secret>`
- **Generate TOTP code**: `desktop-2fa code <issuer>`
- **Remove a token**: `desktop-2fa remove <issuer>`
- **Rename a token**: `desktop-2fa rename <old_issuer> <new_issuer>`
- **Export vault to file**: `desktop-2fa export <path>`
- **Import vault from file**: `desktop-2fa import <path>`
- **Create vault backup**: `desktop-2fa backup`

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
│   ├── model.py        # Vault data models
│   ├── storage.py      # Vault storage logic
│   └── vault.py        # Vault management
├── storage.py          # General storage utilities
└── __init__.py         # Package initialization
tests/
├── __init__.py
├── test_cli.py         # CLI tests
├── test_crypto.py      # Crypto tests
├── test_storage.py     # Storage tests
├── test_totp.py        # TOTP tests
└── test_vault.py       # Vault tests
```

## Testing

Run the test suite using pytest:

```bash
pytest tests/
```

## Vault Format

The vault stores encrypted data in a JSON structure saved as a `.2fa` file. The format includes:

```json
{
  "version": 1,
  "entries": [
    {
      "name": "GitHub",
      "secret": "JBSWY3DPEHPK3PXP",
      "issuer": "GitHub",
      "type": "totp",
      "digits": 6,
      "period": 30
    }
  ]
}
```

Data is encrypted using Argon2 for key derivation and AES-GCM for symmetric encryption.

## 🧭 Roadmap (high‑level)
v0.3.0 — CLI ✓

v0.4.0 — Vault format v2 + migrations

v0.5.0 — Desktop UI prototype

v0.6.x — Rust core (pyo3)

v1.0.0 — Stable release

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests on GitHub.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

## Author

Łukasz Perek