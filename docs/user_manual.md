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
d2fa add ISSUER SECRET
```

**Parameters:**
- `ISSUER`: Name of the service/provider
- `SECRET`: Base32-encoded secret key

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

### Security Notes

- Passwords are never stored or logged
- Use strong, unique passwords
- Consider using password managers for vault passwords
- The vault is encrypted with AES-256-GCM + Argon2

## Vault File Location

By default, the vault is stored at:
- Linux/macOS: `~/.desktop-2fa/vault`
- Windows: `C:\Users\<username>\.desktop-2fa\vault`

The vault file is automatically created on first use.

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

**"Entry 'NAME' not found"**
- The specified entry doesn't exist
- Use `d2fa list` to see available entries

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

1. **Use strong passwords** for your vault
2. **Keep backups** in secure locations
3. **Regularly update** desktop-2fa
4. **Verify secrets** when adding entries
5. **Use password files** for automation (with proper file permissions)
6. **Keep vault file secure** - don't share or store in insecure locations

## Support

For issues and questions:
- Check this manual first
- Review error messages carefully
- Ensure you're using the latest version
- File issues on GitHub if needed

---

*This manual covers desktop-2fa version 0.6.2*