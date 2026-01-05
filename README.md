# 🛡️ Desktop-2FA

A secure, offline two-factor authentication (2FA) manager for desktop environments. Built with Python, featuring strong encryption and no cloud dependencies.

🌐 **Landing Page**: [desktop-2fa.lukasz-perek.workers.dev](https://desktop-2fa.lukasz-perek.workers.dev/)

![PyPI - Downloads](https://img.shields.io/pypi/dm/desktop-2fa)
[![PyPI version](https://img.shields.io/pypi/v/desktop-2fa.svg)](https://pypi.org/project/desktop-2fa/)
![Python versions](https://img.shields.io/pypi/pyversions/desktop-2fa.svg)
![License](https://img.shields.io/github/license/wrogistefan/desktop-2fa)
![Build](https://github.com/wrogistefan/desktop-2fa/actions/workflows/ci.yml/badge.svg)
[![codecov](https://codecov.io/gh/wrogistefan/desktop-2fa/branch/main/graph/badge.svg)](https://codecov.io/gh/wrogistefan/desktop-2fa)

## Features

- **🔐 Vault**: AES-256-GCM encryption with Argon2 key derivation
- **⏱️ TOTP**: RFC 6238 compliant code generation
- **💻 CLI**: Full command-line interface for managing tokens
- **🔓 Stateless**: Every command requires explicit password authentication
- **🛡️ Security**: Configurable password strength enforcement
- **🧪 Testing**: 176 tests with 90% coverage

## Installation

```bash
pip install desktop-2fa
```

Verify installation:

```bash
python -c "import desktop_2fa; print(desktop_2fa.__version__)"
# Output: 0.6.6
```

## Quick Start

```bash
# Add a new TOTP token
d2fa add GitHub GitHub JBSWY3DPEHPK3PXP

# List all entries
d2fa list

# Generate a code
d2fa code GitHub

# Initialize a new vault
d2fa init-vault
```

### Non-Interactive Usage

```bash
# Provide password via command line
d2fa --password mypassphrase add GitHub GitHub JBSWY3DPEHPK3PXP

# Provide password via file
d2fa --password-file /path/to/passphrase.txt add GitHub GitHub JBSWY3DPEHPK3PXP
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `d2fa add <name> <issuer> <secret>` | Add a new TOTP entry |
| `d2fa list` | List all entries |
| `d2fa code <name>` | Generate TOTP code |
| `d2fa rename <old> <new>` | Rename an entry |
| `d2fa remove <name>` | Remove an entry |
| `d2fa export <path>` | Export vault to JSON |
| `d2fa import <path>` | Import from JSON |
| `d2fa backup` | Create a backup |
| `d2fa init-vault` | Initialize new vault |

## Security

The vault uses:
- **AES-256-GCM** for authenticated encryption
- **Argon2id** for key derivation (time_cost=4, memory_cost=128MiB, parallelism=2)
- **Versioned header** for forward compatibility

Every command requires explicit password authentication. No session-based access.

## Documentation

- [User Manual](docs/user_manual.md) - Complete usage guide
- [CLI UX Specification](docs/ux.md) - UX contract and behavior
- [Cryptography](docs/crypto.md) - Security details

## Testing

```bash
pytest tests/  # Run all tests
pytest --cov=src/desktop_2fa  # Run with coverage
```

## Project Structure

```
src/desktop_2fa/
├── cli/           # Command-line interface
├── crypto/        # Encryption utilities
├── totp/          # TOTP generation
├── vault/         # Vault management
├── ui/            # Desktop GUI
└── utils/         # Utilities
```

## License

Apache License 2.0. See [LICENSE](LICENSE) file.

## Author

Łukasz Perek
