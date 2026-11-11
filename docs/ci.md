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
- CLI minimum checks install the built wheel with Typer 0.18.0 and either Click
  8.0.0 or the current Click release on Python 3.11/3.12/3.13. `pip check` and
  `scripts/smoke_cli.py` verify both entry points, subcommand help and synthetic
  CLI create/add/list/code operations outside the checkout without logging codes.
- `CI gate` rejects missing, failed, cancelled or skipped Quality/Tests/Package/CLI-minimum
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

On 2026-11-11, main protection was updated for #83: `CI gate` is required,
bound to the GitHub Actions app (ID 15368), with strict up-to-date checking.
`enforce_admins=true` applies protection to administrators too. Signatures,
linear history, zero required approvals and the prohibitions on force pushes
and deletion were preserved. No additional branch rules were returned by the
rules endpoint at inspection. Administrators can still edit repository settings;
this is not a claim that policy is impossible to change or bypass by other means.

The release PR records the controlled failing-gate and repaired-gate runs and
API mergeability evidence; no failing code was merged. An administrator's API
view is not an impersonated non-administrator test. Required-check configuration
and blocked mergeability establish enforcement without attempting a merge.
Reinspect effective settings before promotion; they are not versioned by YAML.
CodeQL/dependency graph are not a dedicated dependency-CVE audit.

## CLI dependency bounds

The application supports Typer >=0.18.0 and Click >=8.0.0. Typer 0.12.4 fixed
PEP 604 union annotations, but that alone does not address later Click API
changes: 0.16.0 added Click 8.2 support and 0.18.0 fixed Click 8.3 compatibility.
See the [upstream release notes](https://typer.tiangolo.com/release-notes/#0180).
The selected minimum includes those fixes rather than permitting intermediate
Typer versions with known Click incompatibilities. Click is explicit because the
CLI parser imports it when using Typer versions before vendoring. No speculative
upper bound or unrelated dependency pins are added. Newer Typer versions vendor
Click; separate normal-installation CI covers that parser path.

The boundary jobs force the minimum Typer, rather than letting the resolver
upgrade it. Other dependencies resolve normally: this is a CLI boundary check,
not a claim to test every dependency at its historical minimum. Exact resolved
versions are printed by the smoke script. Current Click testing is deliberately
unbounded to detect future incompatibilities before release.
