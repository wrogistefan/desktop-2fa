# Development tools

Use Python 3.11 or later and a repository-local virtual environment. On Windows,
the maintained commands are run from the repository root:

```powershell
.venv/Scripts/python.exe -m pip install --editable ".[dev]"
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m black --check .
.venv/Scripts/python.exe -m mypy src
```

`dev-reset.sh` retains its historical name for callers, but now only creates or
reuses the repository `.venv` and installs development dependencies there. It
requires Bash and a Python interpreter with `venv`/pip (`python3` by default;
override the bootstrap executable with `PYTHON`). It supports POSIX Bash and
Git Bash on Windows, including Windows `.venv/Scripts/python.exe`. It does not
delete personal vault/config files, global entry points/packages, or existing
environments. Invalid environments are preserved and reported as errors. It
does not change the current shell's activation or command cache. There is no
destructive cleanup option and no data recovery step is needed.

GNU make is optional. `make check-all` runs lint, format verification, source
type checking and tests without auto-formatting or fixing files. It selects
the repository environment when available; override with `make PYTHON=python`.
`make lint-fix` and `make format` explicitly modify source files. Use `make -n`
to inspect recipes. Coverage is available through `make test-cov` and
`make test-cov-html`. Dependencies and tool pins come from `pyproject.toml`.

Tooling regression tests run the reset script only in a temporary synthetic
home/project with stubbed Python/pip commands and sentinel data. Do not run
historical reset scripts against your actual home directory.
