# Repository inventory

Inventory for S19 (#50), based on tracked files at `60afdb7` and the active
`pyproject.toml`, imports, entry points, workflows, Makefile and documentation.
This concerns repository files, not local caches, user vaults or environments.

| Candidate | Decision and evidence |
| --- | --- |
| `src/desktop_2fa.egg-info/` | Remove from Git tracking. Generated setuptools metadata reports 0.1.0 while runtime and project metadata report 0.9.0. Hatchling builds from `pyproject.toml`; no active consumer requires these files. Existing `*.egg-info/` ignore remains. |
| `src/desktop_2fa/cli/requirements.txt` | Remove. Incomplete duplicate dependency list, not referenced by build, workflow or active instructions. `pyproject.toml` is authoritative. |
| `fix_readme_images.py` | Remove. One-off README rewrite script, with no active callers or documentation references. Existing image links and assets are retained. |
| `desktop_2fa.app.*`, `utils.time`, `ui_textual.views.*` | Keep. Dormant skeleton modules are importable package paths; removal could break external imports despite no internal callers. No new GUI functionality is claimed. |
| Root completion/update reports and `docs/UX_AUDIT_REPORT.md` | Preserve pending S21 (#52), which will archive them with provenance and repair links. Historical changelog references remain historical. |
| `LICENSE`, `NOTICE`, branding and image assets | Keep. Distribution/legal material and active README/UI assets; no license attribution is removed. |
| `desktop-2fa.code-workspace` | Keep. Tracked editor setup is distinct from generated metadata and may be intentional. |
| `.venv`, build outputs, test/type/lint caches, coverage outputs | Not tracked; preserve local contents. Existing ignores cover them. |
| `tests/fixtures/vaults/*.bin` | Keep unchanged. Immutable synthetic historical compatibility inputs. |
| `dev-reset.sh`, Makefile | Keep for the separate S20 tooling repair (#51). Do not execute the historical reset script. |

The supported module paths and both CLI entry points remain available. Vault
formats, payloads and cryptographic settings are unchanged; no migration is
needed. This inventory does not authorize deleting personal data or caches.

## Isolated package verification

Build wheel and sdist with `python -m build`. Create a fresh temporary virtual
environment, install the built wheel there, copy `scripts/smoke_installed.py`
into a separate temporary working directory and execute it with that
environment's Python. Remove `PYTHONPATH` for that child process. The script
requires imports to resolve inside the environment, compares distribution and
runtime versions, checks retained module paths and both CLI entry points, and
mounts the Textual prototype using a synthetic temporary vault and bundled CSS.
It does not read the user's default vault or clipboard. S22 adds this check to
the release validation graph.
