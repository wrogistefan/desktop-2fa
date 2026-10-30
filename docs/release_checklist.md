# Stabilization and release readiness

Roadmap: [#31](https://github.com/wrogistefan/desktop-2fa/issues/31), milestone 3.
Completing this checklist does not publish a release or certify security.

## Compatibility and version choice

The next release candidate is **0.10.0**, rather than a patch: the roadmap adds
stricter input/schema rejection, reliable failure statuses, concurrency conflicts
and explicit overwrite controls that can affect callers and automation. D2FA v1,
Argon2id parameters, AES-GCM, UTF-8 password derivation and valid TOTP parameters
remain unchanged. Project/runtime metadata on `release/0.10.0-preparation`
now agree on 0.10.0. This branch is a candidate, not a published release.
Merging requires the maintainer's explicit approval; tagging and publication
are separate actions and are not authorized by this checklist.

Supported fixture evidence covers v0.7.3 and v0.8.3 non-empty-password vaults.
Pre-header vaults remain unsupported: preserve the original and recover from a
supported backup or the original providers. Historical empty-password API vaults
must be opened and re-saved with a non-empty password using the previous release
before upgrading. The current loader has no silent fallback or password retry.
See [cryptographic compatibility](crypto.md#compatibility) and the
[fixture inventory](../tests/fixtures/vaults/README.md).

## Criteria to recheck for the exact candidate commit

These are repeatable release requirements. The stabilization evidence below
predates the candidate version bump. The candidate has separate local evidence;
CI must validate its exact commit before release. The tracker records completion
of S01–S22 separately.

- All S01–S22 issues resolved through focused PRs with review evidence.
- Full tests and quality checks pass on the supported runtime/OS matrix.
- RFC 6238 vectors and immutable supported historical-vault round trips pass.
- Wrong password, tampering, malformed data and failed-write preservation pass.
- Password change, encrypted backup/export and recovery pass with synthetic data.
- Built wheel installs outside the checkout; both entry points, versions,
  retained imports and bundled Textual CSS work without a src fallback.
- Tag/version mismatch and failed/skipped validation block publication;
  validated artifacts are reused without rebuilding.
- Code scanning has no remaining open alert introduced by this work.
- Current documentation examples and local relative links are checked.
- Evidence URLs, measured coverage, known skips and remaining limitations
  are recorded below. No release is published as part of stabilization.

## Candidate preparation evidence

Branch: `release/0.10.0-preparation`. The local full suite on Windows/Python
3.13.11 passed: **1052 passed, 7 skipped**, one zxcvbn deprecation warning.
Ruff, Black and source mypy passed. The skips and platform limits described
below still apply. No cryptographic format or parameters changed.

The [synthetic CLI campaign](../scripts/release_cli.py) passed **74 checks**, exercising every command
and recursive help, success/error output modes, password change, encrypted
backup/export/recovery and write refusal. Its [report and captures](
../assets/screenshots/release-0.10.0/README.md) distinguish real subprocesses,
prompt/clipboard stubs and headless Textual. Separate native Windows terminal
checks passed initialization with hidden password/confirmation, interactive add
with hidden secret, and password change followed by reopening the vault.
The generated native-test vault/password files were removed. System clipboard
and native UI checks on other platforms remain manual. PNG and SVG assets
are linked from README.

Both distribution formats built. Installation of the wheel into a separate
venv passed `scripts/smoke_installed.py` with isolated imports and supported
historical fixtures. Twine **7.0.0** accepted both archives; the older local
Twine 6.2.0 rejected metadata version 2.5 and is unsuitable for this build.
The isolated installation resolved current dependencies separately from the
existing development venv. Candidate CI and maintainer approval are pending.
No merge, tag or release has been performed.

## Stabilization evidence (before the candidate version bump)

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
development-tool failure messages. The integrated Quality/Package/CI-gate and
nine-combination runtime results are attached to
[S22 PR #80](https://github.com/wrogistefan/desktop-2fa/pull/80); follow its CI
run for the measured Linux/3.11 `coverage` artifact. No arbitrary percentage
threshold is imposed. Gate/tag regression tests reject mismatches and failed,
skipped or incomplete validation results without creating a release tag.
The [roadmap completion record](https://github.com/wrogistefan/desktop-2fa/issues/31)
records the final successful run, measured coverage and merge results before
closure. Passing checks are required before merging S22; these links are not
permission to publish a release.

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
