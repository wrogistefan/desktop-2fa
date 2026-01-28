# User Manual Update Summary

## Overview
Updated `docs/user_manual.md` to reflect Desktop-2FA version 0.8.1 with zxcvbn password strength integration and reorganized vault command structure.

## Key Updates

### 1. Version Update
- Updated from version 0.8.0 to 0.8.1
- Final line updated: `*This manual covers desktop-2fa version 0.8.1*`

### 2. Vault Command Structure
All vault commands are now organized under the `vault` command group:

**Old Format:**
- `d2fa init-vault`
- `d2fa list`
- `d2fa add`
- `d2fa remove`
- `d2fa rename`
- `d2fa export`
- `d2fa import`
- `d2fa backup`

**New Format:**
- `d2fa vault init`
- `d2fa vault list`
- `d2fa vault add`
- `d2fa vault remove`
- `d2fa vault rename`
- `d2fa vault export`
- `d2fa vault import`
- `d2fa vault backup`

### 3. New Commands Added

#### `vault unlock`
- Unlocks and verifies vault
- Checks password strength if configured
- Shows non-blocking warning for weak passwords

```bash
d2fa vault unlock
```

#### `vault change-password`
- Changes vault password
- Validates new password strength
- Requires interactive mode

```bash
d2fa vault change-password
```

### 4. Password Strength Section Updates

**Changed From:**
- Entropy-based calculation with bits
- Formula: log2(N^L) where N is character set size, L is length

**Changed To:**
- zxcvbn-based evaluation with score 0-4
- Score 0-2: Weak (easily guessable)
- Score 3-4: Strong (resilient to attacks)

**Examples Added:**
- Weak passwords: "password", "123456", "qwerty", "admin2024"
- Strong passwords: "Battery-Horse-Staple", "Mountain@River2024"

### 5. Configuration Updates

**Old Configuration:**
```toml
[security]
min_password_entropy = 60
reject_weak_passwords = false
```

**New Configuration:**
```toml
[security]
# Reject weak passwords (password score < 3)
reject_weak_passwords = false

# Warn when unlocking vault if password is weak
warn_on_weak_existing_passwords = false

# Legacy option (recognized but uses zxcvbn scoring)
min_password_entropy = 60
```

### 6. Password Strength Examples

Added practical examples of password strength feedback:
```
Password too weak (score 1 < 3). This is similar to a word by itself. 
Add another word or two. Otherwise, a few variations of this are very guessable.
Continue with weak password? [y/N]:
```

### 7. Security Best Practices

Enhanced with zxcvbn-specific guidance:
- Added password strength score recommendations (3-4)
- Added examples of strong passwords
- Added warnings about common weak patterns
- Added instruction to test password with `d2fa vault unlock`

### 8. Error Messages

Updated error handling documentation:

**Added:**
- "Password cannot be empty." - new validation check

**Updated:**
- "Password too weak (score X < Y)" - changed from entropy-based

### 9. Examples Throughout

Updated all command examples to use new `vault` command prefix:
- Batch operations
- Backup strategy
- Migration between machines
- Duplicate name resolution

## Sections Modified

1. ✅ Command Reference - `vault init`, `vault list`, `vault add`
2. ✅ New Commands - `vault unlock`, `vault change-password`
3. ✅ Vault Operations - `vault remove`, `vault rename`, `vault export`, `vault import`, `vault backup`
4. ✅ Password Management - Password strength enforcement
5. ✅ Configuration - Updated options and examples
6. ✅ Error Handling - Updated error messages
7. ✅ Advanced Usage - Updated all examples
8. ✅ Troubleshooting - Updated commands and examples
9. ✅ Security Best Practices - Enhanced with zxcvbn guidance
10. ✅ Version Footer - Updated to 0.8.1

## Backward Compatibility Notes

The manual now documents:
- Legacy `min_password_entropy` configuration is still recognized
- Legacy entropy values are automatically mapped to zxcvbn scores
- Old vault formats (pre-0.6.0) are not compatible
- Duplicate names from older versions can be resolved with `vault rename`

## Total Changes

- **Lines Modified:** ~150 lines updated
- **Commands Updated:** 8 vault commands reorganized under `vault` group
- **New Commands Documented:** 2 (`vault unlock`, `vault change-password`)
- **Configuration Options:** Added `warn_on_weak_existing_passwords`
- **Examples Updated:** All command examples reflect new structure
- **Error Messages:** Updated 2 error messages for clarity

## Quality Assurance

✅ All command examples validated against current CLI structure
✅ Password strength examples match zxcvbn actual behavior
✅ Configuration options match `~/.config/d2fa/config.toml` schema
✅ Error messages match actual CLI error output
✅ Backward compatibility notes accurate and clear

---

**Date:** January 28, 2026
**Version:** Desktop-2FA 0.8.1
**Status:** Complete
