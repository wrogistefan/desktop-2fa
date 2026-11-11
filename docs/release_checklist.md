# Release 0.11.0 preparation

On 2026-11-11 the maintainer authorized merging the release PR, creating a
signed v0.11.0 tag, publishing the release and checking the PyPI README.
This checklist records the required validation; follow the GitHub Release
and tag workflow for the exact source, artifacts and publication evidence.

## Scope and compatibility

Version 0.11.0 is a minor release because it completes Textual account/vault
workflows and changes credential-free `d2fa ui` startup to open a locked UI.
Supplied credentials retain CLI pre-startup error statuses. Codes refresh with
entry-specific countdowns. Writes, backup and export authenticate separately;
the session locks manually or after five minutes of inactivity.

D2FA v1, Argon2id/AES-GCM parameters, historical fixture support and CLI account
resolution remain unchanged. No vault migration is required. See
[crypto compatibility](crypto.md#compatibility), [security](SECURITY.md) and the
[Textual threat analysis](textual-security.md). Python cannot guarantee erasure
of decrypted data; passing tests do not constitute a security audit.

The completed UI was merged in [PR #85](https://github.com/wrogistefan/desktop-2fa/pull/85),
merge commit `cae6ec64c4d68a2a0f470f7b7ed79cf17ca66c2d`.
Its final source commit passed the nine OS/Python CI combinations and quality,
package, CodeQL and CI gate checks. Kilo reported no issues; Sourcery skipped
substantive review because its quota was exhausted. These are feature evidence,
not validation of the later release version bump.

## Checks required before publication

- Validate the exact release PR commit: full tests, Ruff, Black, source mypy,
  package build and the Windows/macOS/Linux × Python 3.11/3.12/3.13 CI matrix.
- Check version agreement, wheel/sdist metadata and `twine check`; install the
  wheel outside the checkout and run `scripts/smoke_installed.py` in isolation.
- Run synthetic CLI/UI campaigns. Preserve historical captures and record
  headless/clipboard limits; native clipboard remains a separate manual check.
- Review current documentation, links and the actual package long description.
- Verify [CLI dependency compatibility #82](https://github.com/wrogistefan/desktop-2fa/issues/82)
  with the wheel boundary matrix (minimum Typer, minimum/current Click).
- Reinspect [required merge gate #83](https://github.com/wrogistefan/desktop-2fa/issues/83)
  including administrator enforcement, source app and strict up-to-date checks.
  See [effective policy and limits](ci.md#repository-policy-is-separate).
- For [PyPI README/security documentation #84](https://github.com/wrogistefan/desktop-2fa/issues/84),
  verify pinned absolute image/document URLs and built long descriptions. The
  security text describes the actual 0.11.0 session, superseding the issue's
  originally proposed 0.10.1 target. Production PyPI rendering must still be
  checked after separately authorized publication; preparation cannot prove it.
- Obtain explicit maintainer authorization before merging, tagging or publishing.
  Then require matching tag/version and successful validation, reuse validated
  distribution artifacts, and verify published files and PyPI rendering.

## Evidence

The [original UI screenshots and report](../assets/screenshots/textual-ui/README.md)
use synthetic data and a controlled clock. Their original pre-release captions
are preserved. They do not demonstrate native OS clipboard behavior or a GUI.
The [0.10.0 release record](release-0.10.0-evidence.md) is historical evidence;
its publication authorization applies only to 0.10.0.

Release-branch validation results are recorded in the release PR. A green PR
alone does not authorize publication or verify the future production PyPI page.
