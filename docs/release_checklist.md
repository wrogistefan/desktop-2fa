# Stabilization and release readiness

Roadmap: [#31](https://github.com/wrogistefan/desktop-2fa/issues/31), milestone 3.
Completing this checklist does not publish a release or certify security.

## Compatibility and version choice

The next release candidate is **0.10.0**, rather than a patch: the roadmap adds
stricter input/schema rejection, reliable failure statuses, concurrency conflicts
and explicit overwrite controls that can affect callers and automation. D2FA v1,
Argon2id parameters, AES-GCM, UTF-8 password derivation and valid TOTP parameters
remain unchanged. This is the version choice for later release preparation;
project/runtime metadata remain 0.9.0 until a separately reviewed version bump.
Do not create a v0.10.0 tag against the current metadata.

Supported fixture evidence covers v0.7.3 and v0.8.3 non-empty-password vaults.
Pre-header vaults remain unsupported: preserve the original and recover from a
supported backup or the original providers. Historical empty-password API vaults
must be opened and re-saved with a non-empty password using the previous release
before upgrading. The current loader has no silent fallback or password retry.
See [cryptographic compatibility](crypto.md#compatibility) and the
[fixture inventory](../tests/fixtures/vaults/README.md).

## Evidence to record for the exact candidate commit

- [ ] All S01–S22 issues resolved through focused PRs with review evidence.
- [ ] Full tests and quality checks pass on the supported runtime/OS matrix.
- [x] RFC 6238 vectors and immutable supported historical-vault round trips pass.
- [x] Wrong password, tampering, malformed data and failed-write preservation pass.
- [x] Password change, encrypted backup/export and recovery pass with synthetic data.
- [x] Built wheel installs outside the checkout; both entry points, versions,
  retained imports and bundled Textual CSS work without a src fallback.
- [ ] Tag/version mismatch and failed/skipped validation block publication;
  validated artifacts are reused without rebuilding.
- [x] Code scanning has no remaining open alert introduced by this work.
- [x] Current documentation examples and local relative links are checked.
- [ ] Evidence URLs, measured coverage, known skips and remaining limitations
  are recorded below. No release is published as part of stabilization.

## Evidence log

Local integrated preflight on Windows/Python 3.13.11: **1052 passed, 7 skipped**,
with one existing zxcvbn deprecation warning. Ruff, Black, source mypy and
pinned/checksummed actionlint passed. Native GNU make was unavailable; the
Makefile dry run passed separately with GNU Make 4.3 in WSL. The other local
skips concern filesystem alias support; CI must provide the platform evidence.
No user vault or clipboard was used.

The integrated wheel/sdist built successfully. A fresh temporary Windows venv
outside the checkout passed isolated imports, both entry points, version
agreement, bundled Textual CSS/mount, non-default TOTP parameters, password
change, backup/export recovery and supported historical-vault round trips.
Representative CLI documentation examples and the integrated local relative-file
link scan passed. Historical binary fixtures are unchanged.

CodeQL alert #9 is **fixed**, and the open-alert query returned no alerts after
[security PR #72](https://github.com/wrogistefan/desktop-2fa/pull/72) merged.
Kilo accepted the focused PRs, including corrections to URI-label output and
development-tool failure messages. Final integrated CI matrix/coverage evidence
and the remaining merge results must be recorded before closing the roadmap.

## Remaining limitations

- Python cannot guarantee erasure of passwords/keys. A compromised host or
  observed clipboard can disclose secrets/codes. Weak passwords remain guessable.
- No audit/certification, anti-rollback protection or universal power-loss
  guarantee is claimed; see [persistence limits](persistence.md).
- Textual is a prototype for listing, generation and copy, not entry management.
- External adapters support only the documented fixture variants and are not
  wired into CLI import. Unsupported payload metadata is refused, not migrated.
- Windows captured help on legacy code pages needs UTF-8 mode (`PYTHONUTF8=1`).
- Publication credentials and main branch required-check settings are separate
  from YAML job dependencies. Inspect their state and report any gap explicitly.
