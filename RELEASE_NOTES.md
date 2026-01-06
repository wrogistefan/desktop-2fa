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
