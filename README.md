# 🛡️ Desktop-2FA

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

### From Source

Clone the repository and install dependencies:

```bash
git clone https://github.com/wrogistefan/desktop-2fa.git
cd desktop-2fa
pip install -e .
```

## Usage

Launch the application:

```bash
python -m src.app.main
```

### Adding Tokens

Use the UI to add new TOTP tokens by providing the secret key, issuer, and other details.

### Generating Codes

The application will automatically generate and display TOTP codes based on the current time. Codes are copied to the clipboard for easy use.

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

## Roadmap

- [ ] Export/import to KeePassXC-compatible format
- [ ] Rust migration for crypto core
- [ ] GUI polish and token editing
- [ ] OTP URI parsing and QR code import

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests on GitHub.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

## Author

Łukasz Perek