# Desktop-2FA User Manual

## Overview

Desktop-2FA is a secure, offline two-factor authentication (2FA) manager for desktop environments. It provides a command-line interface for managing TOTP (Time-based One-Time Password) tokens with strong encryption and no cloud dependencies.

## Quick Start

### Installation

```bash
pip install desktop-2fa
```

### First Use

1. Initialize your vault:
```bash
d2fa init-vault
```

2. Add your first TOTP token:
```bash
d2fa add GitHub JBSWY3DPEHPK3PXP
```

3. Generate a code:
```bash
d2fa code GitHub
```

## Commands

### Global Options

All commands support these options:

- `--password PASSWORD`: Provide password directly
- `--password-file FILE`: Read password from file
- `--allow-weak-passwords`: Allow weak passwords (bypasses strength checks and unlock timeout)
- `--help`: Show help for the command

### `init-vault` - Initialize New Vault

Creates a new encrypted vault file.

```bash
d2fa init-vault [--force]
```

**Options:**
- `--force`: Overwrite existing vault

**Examples:**
```bash
# Create new vault (interactive password prompt)
d2fa init-vault

# Overwrite existing vault
d2fa init-vault --force

# Create vault with password from file
d2fa init-vault --password-file ~/.vault_pass
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
d2fa add [ISSUER] [SECRET]
```

**Parameters:**
- `ISSUER`: Name of the service/provider (optional in interactive mode)
- `SECRET`: Base32-encoded secret key (optional in interactive mode)

**Interactive Mode:**
When run in a terminal without arguments, prompts for issuer and secret:
```bash
d2fa add
Issuer: GitHub
Secret: JBSWY3DPEHPK3PXP
```

**Examples:**
```bash
# Add entry interactively (prompts for missing values)
d2fa add

# Add with arguments
d2fa add GitHub JBSWY3DPEHPK3PXP

# Add using otpauth URL
d2fa add "otpauth://totp/GitHub:user?secret=JBSWY3DPEHPK3PXP&issuer=GitHub"

# Add with password from command line
d2fa add GitHub JBSWY3DPEHPK3PXP --password mypassword
```

**Notes:**
- Secrets must be valid Base32
- otpauth URLs are automatically parsed
- If vault doesn't exist, it will be created automatically
- In interactive mode, the secret is entered visibly (not hidden)

### `code` - Generate TOTP Code

Generates and displays the current TOTP code for an entry.

```bash
d2fa code NAME
```

**Parameters:**
- `NAME`: Issuer or account name

**Examples:**
```bash
d2fa code GitHub
# Output: 123456

d2fa code "Google:personal"
# Output: 789012
```

### `remove` - Remove Entry

Deletes a TOTP entry from the vault.

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

Changes the name of an existing entry.

```bash
d2fa rename OLD_NAME NEW_NAME
```

**Parameters:**
- `OLD_NAME`: Current issuer/account name
- `NEW_NAME`: New name

**Examples:**
```bash
d2fa rename GitHub GitHub-work
# Output: Renamed 'GitHub' → 'GitHub-work'
```

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
   d2fa list --password mypassword
   ```

3. **Password File**:
   ```bash
   echo "mypassword" > ~/.vault_pass
   d2fa list --password-file ~/.vault_pass
   ```

### Vault Unlock Timeout

After successfully entering the vault password, the vault remains "unlocked" for 15 minutes. During this period:

- You can provide the password via `--password` or `--password-file` without being prompted again
- The unlock state is tracked via a timestamp file (`.vault-unlocked`) in the vault directory
- No passwords are stored on disk - only the unlock timestamp

```bash
# First command requires password
d2fa list --password mypassword

# Subsequent commands within 15 minutes can use --password without prompting
d2fa code GitHub --password mypassword
d2fa add AWS ABCDEF123456 --password mypassword
```

**Security Note:** The vault always requires the real master password for decryption. The unlock timeout only skips the password prompt when the password is provided via command-line options.

### Password Strength Enforcement

Desktop-2FA can enforce password strength requirements when creating new vaults. Configure via `~/.config/d2fa/config.toml`:

```toml
[security]
min_password_entropy = 60
reject_weak_passwords = false
```

- **min_password_entropy**: Minimum entropy bits required (default: 60)
- **reject_weak_passwords**: If true, reject weak passwords; if false, warn and allow continuation

Entropy calculation:
- Passphrases (4+ words): 11 bits × number of words
- Passwords: log2(N^L) where N is character set size, L is length

**Bypass:** Use `--allow-weak-passwords` or set `D2FA_ALLOW_WEAK_PASSWORDS=1` to skip checks.

### Security Notes

- Passwords are never stored or logged (except temporarily in memory)
- Use strong, unique passwords
- Consider using password managers for vault passwords
- The vault is encrypted with AES-256-GCM + Argon2
- The unlock file contains only a timestamp, no sensitive data
- The vault always requires the real master password for decryption

## Configuration

Desktop-2FA can be configured via `~/.config/d2fa/config.toml`:

```toml
[security]
min_password_entropy = 60
reject_weak_passwords = false
```

### Configuration Options

- **min_password_entropy** (default: 60): Minimum password entropy in bits
- **reject_weak_passwords** (default: false): Whether to reject weak passwords or just warn

The config file is optional - defaults are used if the file doesn't exist.

## Vault File Location

By default, the vault is stored at:
- Linux/macOS: `~/.desktop-2fa/vault`
- Windows: `C:\Users\<username>\.desktop-2fa\vault`

The vault file is automatically created on first use.

**Unlock File:** A `.vault-unlocked` file in the same directory tracks unlock state (contains only a timestamp).

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

**"Password too weak (entropy X < Y)"**
- The vault password doesn't meet strength requirements
- Either strengthen the password or use `--allow-weak-passwords`
- Configure requirements in `~/.config/d2fa/config.toml`

**"Passwords do not match"**
- Confirmation password doesn't match the initial password
- Re-run the command and ensure both passwords are identical

**"Error: Cannot specify both --password and --password-file"**
- You provided both password options simultaneously
- Use only one: either `--password` or `--password-file`

**"Error: Password not provided and not running in interactive mode"**
- No password source available in non-interactive environment
- Provide `--password` or `--password-file`, or run in a terminal

**"Error: Vault is unlocked but password not provided. Use --password or --password-file."**
- The vault unlock timeout has not expired, but no password was provided via options
- Provide the password using `--password` or `--password-file`

## Advanced Usage

### Batch Operations

```bash
# Add multiple entries
d2fa add GitHub JBSWY3DPEHPK3PXP
d2fa add AWS ABCDEFGHIJKLMNOP
d2fa add Google QRSTUVWXYZ123456

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
d2fa init-vault

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

- Vaults created with desktop-2fa 0.6.0+ are forward compatible
- Older vaults (pre-0.6.0) are not compatible and must be recreated

## Command Reference

```bash
d2fa --help                    # Show general help
d2fa COMMAND --help           # Show help for specific command
d2fa --version                # Show version
d2fa                         # Show version (no args)
```

## Security Best Practices

1. **Use strong passwords** for your vault (configure minimum entropy in config)
2. **Keep backups** in secure locations
3. **Regularly update** desktop-2fa
4. **Verify secrets** when adding entries
5. **Use password files** for automation (with proper file permissions)
6. **Keep vault file secure** - don't share or store in insecure locations
7. **Be aware of unlock timeout** - vault remains accessible for 15 minutes after unlock
8. **Use `--allow-weak-passwords`** only when necessary (testing, legacy systems)
9. **Configure password policies** in `~/.config/d2fa/config.toml` for your security requirements

## Support

For issues and questions:
- Check this manual first
- Review error messages carefully
- Ensure you're using the latest version
- File issues on GitHub if needed

---

*This manual covers desktop-2fa version 0.6.3*