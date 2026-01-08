# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.7.3] — DEF-02 PermissionDenied Fix

### 🐛 Fixed

#### DEF-02: PermissionDenied Not Caught During Vault Creation (HIGH)

When creating a new vault (when vault file doesn't exist), the CLI would attempt to save the vault file. If the directory was not writable, `vault.save()` raised `PermissionDenied`, but this exception was NOT caught in the "create new vault" paths, resulting in a full Python traceback.

- Added `try/except PermissionDenied` blocks around all `vault.save()` calls in vault creation paths
- Functions fixed:
  - `add_entry_interactive()`
  - `list_entries()` (both vault creation paths)
  - `add_entry()` (both vault creation paths)
  - `init_vault()` (already had the fix)
- Users now see: `Cannot access vault directory (permission denied).` instead of a traceback

### 📚 Documentation
- Updated CHANGELOG with DEF-02 fix details
- Updated version to 0.7.3

---

## [0.7.2] — Security & Reliability Patch

### 🛡️ Security Fixes

#### DEF-01: Empty Password Hard-Rejection (CRITICAL)

Empty passwords are now immediately rejected with a clear error message. Previously, empty passwords could be accepted during vault creation, bypassing entropy calculations and confirmation prompts.

- Added immediate validation for empty passwords in `get_password_for_vault()` function
- Empty passwords are rejected before any entropy calculation
- Error message: `Password cannot be empty.`
- Applies to all password input methods: interactive prompts, `--password` flag, and `--password-file`

#### DEF-02: PermissionError Handling (HIGH)

Permission errors are now properly distinguished from vault-not-found errors. The application no longer treats permission denied errors as missing vault files, preventing unnecessary password prompts and vault creation attempts.

- Added `PermissionDenied` and `VaultNotFound` exception classes for precise error handling
- `Vault.load()` now distinguishes between `FileNotFoundError` and `PermissionError`
- `Vault.save()` properly handles `PermissionError` with user-friendly messages
- On permission errors, the CLI:
  - Does NOT prompt for password
  - Does NOT attempt to create a vault
  - Shows: `Error: Cannot access vault directory (permission denied).`
  - No Python stack traces are shown to users

### 📚 Documentation
- Updated RELEASE_NOTES.md with detailed security fix documentation
- Updated README.md for version 0.7.2
- Added password validation rules section to user manual
- Added permission denied error handling documentation

### 🧪 Testing
- Updated `test_vault_load_file_not_found` to expect new error message
- All 187 tests pass

---

## [0.7.1] — Security Patch

### 🛡️ Security Hardening
- Fixed a CodeQL-reported issue where sensitive information could be exposed through printed output.
- Improved output sanitization to ensure no secrets or password-related data appear in logs or CLI messages.
- No functional changes.

---

## [0.7.0] — Vault Semantics & Deterministic UX

### ✨ New Features
- **Explicit Vault Initialization**: Introduced clear separation between vault creation and loading
- **Deterministic Vault Creation Messages**: Vault creation now always prints `Vault created at <path>` regardless of interactive mode
- **Rename Safety**: Added duplicate detection to `rename` command to prevent ambiguous operations

### 🛡️ Security & UX Improvements
- Removed silent vault creation in all modes
- Vault creation is now explicitly announced with the vault path
- Rename command aborts when multiple entries match the target name, ensuring deterministic behavior
- Missing or invalid password now exits cleanly with `typer.Exit(1)`

### 🐛 Fixed
- **#9**: Rename semantics now abort when duplicate entries exist
- **#5**: Explicit vault initialization with clear user feedback

### 🧪 Testing
- Added regression tests for rename with duplicates (abort)
- Added regression tests for rename with no duplicates (success)
- Added regression tests for vault lifecycle (creation, loading, password handling)

### 📚 Documentation
- Added "Vault Lifecycle" section to README
- Documented vault creation and loading behavior
- Documented duplicate entry handling
- Updated CHANGELOG with 0.7.0 release notes

---

## [0.6.6.2] — Security Fix

### 🛡️ Security Hardening
- Fixed a CodeQL-reported issue where an exception message could leak sensitive information when reading a password file failed.
- Removed password file path from error messages to prevent information disclosure.

---

## [0.6.6.1] — 2026-01-05

## [0.6.6] - 2026-01-05

### 🐛 Fixed
- **UX-001 Critical**: Non-interactive `d2fa list --password` no longer creates vault silently
- **UX-008 Medium**: "Vault created." message is now always printed regardless of interactive mode
- **UX Contract Update**: Added new principle: "All state-mutating operations MUST emit confirmation messages regardless of interactive mode."

### 🧪 Testing
- Added regression test `test_list_entries_noninteractive_creates_vault_with_messages`
- Added regression test `test_add_entry_noninteractive_creates_vault_with_messages`

### 📚 Documentation
- Updated docs/ux.md with new UX contract principle
- Updated version to 0.6.6 in all documentation

## [0.6.5] - 2026-01-04

### 🔄 Vault Entry Identification
- **Unique Identifier**: Established `account_name` as the unique identifier for TOTP entries
- **Rename Command**: Implemented `d2fa rename <old> <new>` to rename entries, updating both account name and issuer
- **Migration Warning**: Added detection and warning for vaults with duplicate names from older versions
- **Double Naming Resolution**: Users can now resolve naming conflicts using the rename command

### 🛡️ Security Cleanup
- **Removed Unlock Timeout**: Eliminated misleading unlock timeout feature that had no effect in stateless CLI
- **Stateless Design**: Enforced that every command requires explicit password authentication
- **Codebase Cleanup**: Removed all unlock-related logic, variables, and dead code
- **Test Cleanup**: Removed tests referencing unlock timeout behavior

###  Documentation
- Updated user manual to reflect current vault logic and entry identification
- Documented the rename command and its usage
- Explained migration implications for vaults with duplicate names
- Removed all references to unlock timeout and session-based behavior
- Updated manual version to 0.6.5

### 🛠️ CI Improvements
- Added full matrix CI workflow for Linux, macOS, and Windows with Python 3.12
- Added dedicated macOS job with Qt6 installation for GUI testing
- Streamlined CI steps for faster, deterministic builds

## [0.6.4] - 2026-01-04

### 🎨 CLI Output Standardization
- **Fixed Rich markup in Typer prompts**: Eliminated literal "[cyan]..." output by separating Rich rendering from Typer input prompts
- **Standardized colored output**: Enforced single Rich-first pattern for all CLI output using `rprint(Text(message, style="color"))`
- **Color palette normalization**: Consistent use of cyan (prompts), green (success), yellow (warnings), red (errors), white (info), bold white (headers)
- **Regression test added**: `test_no_rich_markup_in_prompts()` prevents future introduction of markup in prompts
- **Preserved all existing logic**: No changes to password validation, vault behavior, or command semantics


## [0.6.3.1] - 2026-01-04

### 📚 Documentation
- Updated documentation for password handling fix to clarify security requirements.

---

## [0.6.3] - 2026-01-04

### 🛡️ Security Hardening
- **Vault Unlock Security**: Ensured `.vault-unlocked` file contains only timestamp (mtime) with no sensitive data storage.
- **Password Requirement Enforcement**: Vault unlock timeout requires explicit password provision via `--password` or `--password-file` options.
- **Regression Test Added**: `test_unlock_timeout_does_not_bypass_password()` ensures unlock status never bypasses password requirements.

### ✨ New Features
- **Interactive `d2fa add` improvements**: Secret input is now visible (not hidden) for better user experience. Issuer prompts use Rich formatting for cyan color rendering.
- **Password strength enforcement**: Configurable password policy via `~/.config/d2fa/config.toml` with entropy checking and warnings/rejection.
- **CLI bypass flags**: `--allow-weak-passwords` flag and `D2FA_ALLOW_WEAK_PASSWORDS=1` environment variable to skip password checks for testing/legacy scenarios.

### 📚 Documentation
- **User manual updates**: Comprehensive documentation of unlock timeout behavior, password strength configuration, new CLI options, and error messages.
- **Security clarifications**: Clear explanations that vault always requires the real master password for decryption.

### 🐛 Fixed
- **Type annotations**: Fixed MyPy errors for generic dict types.
- **Code formatting**: Applied Black formatting to maintain code style consistency.

### 🧪 Testing
- **All tests pass**: 163 tests passing with full coverage maintained.
- **CI compliance**: Ruff, Black, MyPy, and pytest all pass successfully.

---

## [0.6.2] - 2026-01-03

### 🐛 Fixed
- **CI workflow issues**: Fixed Ruff linting errors, Black formatting issues, and MyPy type checking errors to ensure all CI checks pass
- **Test failures**: Corrected test cases for malformed JSON validation and added proper password handling in vault load tests

### 📚 Documentation
- Added prominent vault format incompatibility warning to README.md, CHANGELOG.md, docs/crypto.md, and docs/ux.md
- Clarified that vaults created prior to 0.6.0 are not compatible with 0.6.0+

---

## [0.6.1] - 2026-01-03

### 📚 Documentation
- Added prominent vault format incompatibility warning to README.md, CHANGELOG.md, docs/crypto.md, and docs/ux.md
- Clarified that vaults created prior to 0.6.0 are not compatible with 0.6.0+

---

## [0.6.0] - 2026-01-03

### 🛡️ Security Audit Completion
- Completed Phase 5: Cryptography Parameter Audit
- Updated Argon2id parameters: time_cost=4, memory_cost=128 MiB, parallelism=2
- Documented cryptographic contracts and parameters
- Validated AES-GCM usage and nonce handling
- Added comprehensive test matrix for vault security phases

### ⚠️ Vault Format Breaking Change
Starting with desktop‑2fa 0.6.0, the vault file format has been fully audited and stabilized as part of the Vault Security Audit (Phases 1–5).

This audit introduced a strict, versioned vault header and hardened cryptographic parameters.

As a result:

Vaults created with versions prior to 0.6.0 are not compatible with 0.6.0+.

Older vaults did not include:

- a version field in the header,
- the finalized magic header (D2FA),
- the audited Argon2id parameters,
- the stable ciphertext layout introduced after the audit.

Because these fields are now required for safe parsing and forward compatibility, vaults created before the audit cannot be imported by current versions of the application.

This is intentional and was required to guarantee:

- deterministic parsing rules,
- safe rejection of malformed or ambiguous vaults,
- future‑proofing for format evolution,
- cryptographic correctness validated in the audit.

#### What this means for users
If your vault was created with 0.5.6 or earlier, it will be rejected as "unsupported format".

You will need to initialize a new vault using `d2fa init-vault`.

All vaults created with 0.6.0 and later include a versioned header and will remain compatible with future releases.

#### Why no automatic migration?
The pre‑audit vaults lacked the metadata required to safely migrate them:

- no version field → impossible to reliably detect layout,
- inconsistent Argon2id parameters → unsafe to reinterpret,
- no stable header → cannot distinguish valid vaults from corrupted files,
- ciphertext structure changed during the audit.

Attempting to "guess" the format would introduce ambiguity and weaken the security guarantees established by the audit.

#### Going forward
From 0.6.0 onward:

- every vault includes a versioned header,
- the format is stable and forward‑compatible,
- future changes will be handled through explicit version bumps,
- no further breaking changes are expected.

This ensures that vaults created today will remain readable in all future versions.

### 🐛 Fixed
- **CI workflow issues**: Fixed import sorting and code formatting to pass Ruff and Black checks
- **Test failure**: Corrected `test_cli_import` to use `--force` flag when importing into existing vault

### 📊 Quality Improvements
- Created tests/vault_matrix.md with complete security test coverage
- All CI checks now pass: Ruff linting, Black formatting, MyPy type checking, and full test suite
- Codebase fully compliant with project's code quality standards

---

## [0.5.6] - 2026-01-01

### 📦 Maintenance
- Sync version with PyPI release.

---

## [0.5.5.2] - 2026-01-01

### 📊 Quality Improvements
- Clarified test coverage: Remaining uncovered lines are standard success-path print statements already exercised by tests but not detected by the coverage tool. No complex mocking or artificial test cases were introduced to inflate coverage.

---

## [0.5.5.1] - 2026-01-01

### 🐛 Fixed
- **Vault initialization**: `Vault.load()` now creates and saves an empty vault file if none exists
- Resolves issue where CLI commands like `list` and `add` failed silently due to missing vault file
- Method now requires a password to persist the vault

### ⚠️ Notes
- This introduces a side-effect in `load()` — consider separating creation logic in future
- TODO: Refactor `load()` → `ensure_vault()` to separate concerns

---

## [0.5.5] - 2025-12-31

### 🛡️ Security Enhancements
- Implemented secure vault password system with mandatory user passphrase
- Added CLI flags --password and --password-file for password input
- Interactive prompt for password entry

### Added
- Importers for popular TOTP formats: Aegis JSON, Bitwarden CSV, 1Password CSV, otpauth URI, FreeOTP XML

---

## [0.5.4] - 2025-12-30

### 📊 Quality Improvements
- Achieved 100% test coverage across all modules
- Removed duplicate Python version badge from README
- Added comprehensive tests for CLI interactive features and error handling

---

## [0.5.3] - 2025-12-30

### 🛡️ Security & Validation Improvements
- Added input validation for `add` command to prevent adding entries with invalid Base32 secrets or empty issuer names
- Improved user experience by providing clear error messages for invalid inputs

### Added
- Official support for Python 3.13
- PyPI monthly downloads badge in README

---

## [0.5.1] - 2025-12-30

### 💻 CLI Enhancements
- Added `--version` option to display app version
- Running the app without arguments now prints the version
- Made `add` command interactive: prompts for issuer and secret if not provided as arguments

---

## [0.5.0] - 2025-12-30
### 🔄 Major Changes
- Migrated vault system to Pydantic v2 for data validation and type safety

### 🏦 Vault Improvements
- Introduced `TotpEntry` and `VaultData` Pydantic models
- Automatic validation of Base32 secrets and positive periods
- Enhanced data integrity with structured models

### ⏱️ TOTP Generator Updates
- No changes, remains RFC 6238 compliant

### 💻 CLI Updates
- Changed `generate` command to `code` for consistency
- Updated entry identification to use `account_name`
- Improved error handling and validation

### 🧪 Testing Improvements
- Achieved 100% test coverage across all modules
- Added tests for new Pydantic models and validation

### 🧹 Internal Cleanup
- Refactored vault implementation to use Pydantic models
- Updated dependencies to include Pydantic v2

### 💥 Breaking Changes
- Vault format changed from custom dict to Pydantic models
- CLI command `generate` renamed to `code`
- JSON export/import format updated to match new models
- `entry.name` replaced with `entry.account_name`

## [0.4.1] - 2025-12-29
### Improved
- Added missing docstrings across the entire codebase.
- Standardized all docstrings to Google-style format.
- Ensured consistent English-language documentation throughout the project.
- Improved clarity and maintainability of crypto, vault, TOTP, and CLI modules.
- Translated remaining non-English comments to English.
- Enhanced developer experience and future documentation generation readiness.

### Notes
This release contains no functional changes. It focuses entirely on documentation quality, readability, and internal consistency.


## [0.4.0] — 2025-12-28

### 🔐 Vault encryption overhaul
- Migrated vault storage to AES-GCM encryption with Argon2 key derivation
- Removed legacy plaintext `storage.py` module
- Vault now saves as binary `.bin` file in `~/.desktop-2fa/vault`
- Backup created automatically as `vault.backup.bin`

### 🧪 Full CLI test coverage
- Added complete test suite for CLI commands: add, list, remove, rename, export, import, backup
- All edge cases and error paths covered
- CLI now fully deterministic and testable

### 🔢 RFC-compliant TOTP generator
- Supports SHA1, SHA256, SHA512
- Configurable digits and period
- Fully tested with deterministic outputs

### 🧼 Codebase cleanup
- Applied `ruff`, `black`, and `mypy` across all modules
- Removed dead code and unused imports
- CI now runs on Python 3.11 and 3.12

### 📊 Coverage milestone
- Achieved 99% test coverage across all modules
- Vault, CLI, crypto, and TOTP fully covered


## [0.3.0] – 2025‑12‑28

### Added
- Full CLI command set: `list`, `add`, `code`, `remove`, `rename`, `export`, `import`, `backup`.
- Encrypted vault implementation using AES‑256‑GCM and Argon2.
- RFC 6238‑compliant TOTP generator.
- Comprehensive test suite covering CLI, crypto, storage, and models.
- New CI workflow with pytest, mypy, ruff, and black.
- Development installation via `pip install -e .`.

### Fixed
- Mypy configuration detection in CI.
- CLI inconsistencies after project restructuring.
- Removed outdated entry point `desktop_2fa.app.main:main`.

### Changed
- Unified CLI entry point: `desktop-2fa = desktop_2fa.cli.main:app`.
- Cleaned up project structure and module layout.
- Updated documentation and usage examples.

### Removed
- Deprecated modules and unused entry points.

## [0.2.1] – 2025-12-27
### Added
- Fully automated PyPI publishing workflow (GitHub Actions).
- Signed Git tag for secure release distribution.
- Synchronized versioning across pyproject.toml, desktop_2fa.__version__, and Git tag.

### Changed
- Updated internal version to match the published package.
- Improved consistency between package metadata and runtime version.

### Fixed
- Resolved version mismatch where Python imported an older module copy.
- Eliminated stale Windows Store Python site-packages conflicts.
- Ensured clean installation from PyPI (pip install desktop-2fa now reports correct version).

---

## [0.2.0] – 2025-12-27
### Added
- First official release prepared for publication on PyPI.
- Stable package build (sdist + wheel) passing all local tests.
- GPG‑signed release tag for distribution integrity.
- GitHub Actions workflow for automated PyPI publishing.

### Changed
- Cleaned and unified project structure and build configuration.
- Updated and aligned project metadata in `pyproject.toml`.

### Fixed
- Removed all TestPyPI‑related issues and 403 errors caused by sandbox limitations.

---

## [0.1.1] – 2025-12-27
### Added
- Complete project layout under `src/`.
- TOTP generator compliant with RFC 6238.
- Argon2 key derivation and AES‑GCM encryption pipeline.
- Vault model, serialization logic, and secure storage layer.
- Full test suite (crypto, TOTP, storage, vault).
- Tooling configuration: Ruff, Black, mypy (strict mode).
- Initial GitHub Actions workflow for packaging and testing.

### Changed
- Refactored codebase for clarity, maintainability, and CI compatibility.

---

## [0.1.0] – 2025-12-26
### Added
- Initial project scaffold and directory structure.
- Minimal TOTP and storage prototype.
