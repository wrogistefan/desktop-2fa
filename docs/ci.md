# CI and release gates

One workflow owns Quality, Tests, Package, the aggregate **CI gate**, and tag
publication. Pull requests/main pushes validate code; `v*` tags use the same
graph. CodeQL remains GitHub default setup, outside this workflow.

- Quality runs Ruff, Black, source mypy and pinned upstream actionlint. Python
  3.11 is the common minimum for runtime, Black, Ruff and mypy configuration.
  Run `python scripts/check_workflows.py` locally with network access to fetch
  the pinned actionlint binary and verify its upstream checksum. The version
  has one source: `.github/actionlint-version`.
- Tests cover Windows, macOS and Linux with Python 3.11, 3.12 and 3.13 (nine
  combinations), without fail-fast cancellation. These are the declared tested
  versions. Metadata remains `>=3.11`; newer Python versions may install but
  are best effort until added to the matrix. The formerly duplicate macOS job
  is removed. Start with this full matrix; narrow only with reviewed evidence.
- Coverage is collected once on Linux/3.11 and uploaded as evidence. There is
  no arbitrary percentage gate; record the measured baseline for the exact run.
- Package builds wheel/sdist, checks metadata, rejects tag/version mismatch and
  installs the wheel into a fresh environment outside the checkout. The smoke
  script checks import origin, both entry points, versions, retained module
  paths, a synthetic password change, backup/export/recovery, supported immutable
  historical fixtures and a headless Textual mount with packaged CSS. Fixture
  inputs are copied separately; the installed package cannot import checkout src.
- `CI gate` rejects missing, failed, cancelled or skipped Quality/Tests/Package
  results. Publication requires the successful gate and Package job, downloads
  the already checked distributions, and does not rebuild. Publishing still
  uses the existing `PYPI_TOKEN` secret; no credential migration is included.
- Permissions are read-only for repository contents; unused global
  `security-events: write` is removed. Publishing credentials exist only in the
  upload step. Jobs have timeouts, pip download caching, and superseded PR runs
  are cancelled. Main/tag runs are not cancelled by that PR policy.

`tests/test_release_checks.py` tests tag mismatch and failed/skipped/incomplete
graph rejection. Actionlint checks workflow structure and expression syntax.
The package/tag checks themselves do not create a tag or publish a release.

## Repository policy is separate

At inspection before S22, main branch protection had no required status checks
and required zero approving reviews. A green workflow does not itself enforce
branch protection. Adding `CI gate` as a required branch check is a separate
repository-setting change; this implementation does not silently alter that
policy. Verify/report settings separately before release/promotion. This is
distinct from the YAML graph, which blocks tag publication on failed/skipped
validation. CodeQL/dependency graph are not a dedicated dependency-CVE audit.
