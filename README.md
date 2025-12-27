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

Expected output: `0.2.1`

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

```bash
desktop-2fa-cli list
desktop-2fa-cli add github JBSWY3DPEHPK3PXP
desktop-2fa-cli code github
```

## Project Structure

```
src/
├── app/          # Application entry point, clipboard handling, and configuration
├── crypto/       # Cryptographic utilities (AES-GCM, Argon2)
├── totp/         # TOTP code generation (RFC 6238 compliant)
├── ui/           # Desktop UI components and dialogs
├── utils/        # Utility functions (e.g., time helpers)
└── vault/        # Vault model, storage, and logic
tests/            # Unit tests for all modules
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
v0.3.0 — CLI

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