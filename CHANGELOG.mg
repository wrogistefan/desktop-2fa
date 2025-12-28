# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

---
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
