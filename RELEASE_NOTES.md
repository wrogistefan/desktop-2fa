# Release Notes for Desktop-2FA 0.7.3

## DEF-02 PermissionDenied Fix

This release completes the DEF-02 security fix by ensuring PermissionDenied exceptions are properly caught during vault creation operations.

### Changes

Added `try/except PermissionDenied` blocks around all `vault.save()` calls in vault creation paths:
- `add_entry_interactive()`
- `list_entries()` (both vault creation paths)
- `add_entry()` (both vault creation paths)
- `init_vault()` (already had the fix)

### User-Facing Behavior

When permission errors occur during vault creation, users now see:
```
Cannot access vault directory (permission denied).
```

Instead of a Python traceback.

### Compatibility

- This release maintains full backward compatibility with existing vaults
- No changes to the vault file format
- Existing data is preserved

---

# Release Notes for Desktop-2FA 0.7.2

## Security & Reliability Patch

This release addresses security and reliability issues identified in the security test report, improving password validation and error handling for filesystem permission errors.

### Security Fixes

#### DEF-01: Empty Password Hard-Rejection (CRITICAL)

Empty passwords are now immediately rejected with a clear error message. Previously, empty passwords could be accepted during vault creation, bypassing entropy calculations and confirmation prompts.

**Changes:**
- Added immediate validation for empty passwords in `get_password_for_vault()` function
- Empty passwords are rejected before any entropy calculation
- Error message: `Password cannot be empty.`
- Applies to all password input methods: interactive prompts, `--password` flag, and `--password-file`

#### DEF-02: PermissionError Handling (HIGH)

Permission errors are now properly distinguished from vault-not-found errors. The application no longer treats permission denied errors as missing vault files, preventing unnecessary password prompts and vault creation attempts.

**Changes:**
- Added `PermissionDenied` and `VaultNotFound` exception classes for precise error handling
- `Vault.load()` now distinguishes between `FileNotFoundError` and `PermissionError`
- `Vault.save()` properly handles `PermissionError` with user-friendly messages
- On permission errors, the CLI:
  - Does NOT prompt for password
  - Does NOT attempt to create a vault
  - Shows: `Error: Cannot access vault directory (permission denied).`
  - No Python stack traces are shown to users

### UX Improvements

- All error messages are now user-friendly without exposing internal implementation details
- Mutating operations (save, import, backup) are blocked when permissions are insufficient
- Atomic write behavior is preserved for vault operations

### Compatibility

- This release maintains full backward compatibility with existing vaults
- No changes to the vault file format
- Existing data is preserved

### Reference

- Security Test Report: DEF-01 (Empty Password Rejection)
- Security Test Report: DEF-02 (PermissionError Handling)

---

# Release Notes for Desktop-2FA 0.7.1

## Security Patch

This release is a security patch addressing a CodeQL-reported issue where sensitive information could be exposed through error messages and logging.

### Security Fixes

- **Clear-text Logging Prevention**: Fixed an issue where exception details could be included in error messages, potentially exposing sensitive file paths or system information
- **Output Sanitization**: Improved error handling to ensure no secrets, passwords, or sensitive data appear in logs or CLI messages
- **Bare Exception Handling**: Replaced broad `except Exception:` blocks with more specific `except OSError:` to reduce the risk of catching and exposing unexpected exceptions

### Changes

- `vault.py`: Removed exception message from `VaultIOError` messages to prevent information disclosure
- `helpers.py`: Replaced bare `except Exception:` with `except OSError:` in password file reading functions

### Compatibility

- This release maintains full backward compatibility with existing vaults
- No changes to the vault file format
- No functional changes to user-facing behavior

### Reference

- CodeQL Alert: Clear-text logging of sensitive information

---

# Release Notes for Desktop-2FA 0.7.0

## Vault Semantics & Deterministic UX

This release introduces explicit vault initialization semantics and deterministic rename behavior.

### Key Changes

#### 1. Explicit Vault Initialization (#5)

- **Clear separation** between vault creation and loading
- **Always announces** vault creation with message: `Vault created at <path>`
- **No silent creation** in any mode (interactive or non-interactive)
- **Clean error handling** for missing/invalid passwords (exits with `typer.Exit(1)`)

#### 2. Safe Rename Semantics (#9)

- **Duplicate detection**: The `rename` command now checks for multiple entries matching the target name before any mutation
- **Abort on duplicates**: If multiple entries match, the command aborts with a clear error message:
  ```
  Error: Multiple entries named '<name>' exist. Operation aborted. Resolve duplicates first.
  ```
- **No partial renames**: Ensures deterministic behavior when duplicates exist

### What's New

- Added `create_vault()` helper function for consistent vault creation
- Added `find_entries()` method to Vault class for duplicate detection
- Updated all vault-creating commands to use consistent messaging
- Added comprehensive regression tests for vault lifecycle and rename semantics

### Documentation

- New "Vault Lifecycle" section in README
- Updated documentation for duplicate entry handling
- Clearer error messages for password-related issues

### Compatibility

- This release maintains backward compatibility with existing vaults
- No changes to the vault file format
- Existing data is preserved

### Testing

- 180+ tests passing
- Added regression tests for:
  - Rename with duplicates (abort)
  - Rename with no duplicates (success)
  - Vault creation with path announcement
  - Password handling in non-interactive mode

### Thank You

Thanks to the community for reporting these UX issues and helping improve Desktop-2FA!
