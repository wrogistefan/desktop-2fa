#!/usr/bin/env bash
# Historical name retained: this now reinstalls only the project environment.
set -euo pipefail

if [[ $# -gt 0 ]]; then
    if [[ $# -eq 1 && "$1" == "--help" ]]; then
        echo "Usage: ./dev-reset.sh"
        echo "Create/reuse the repository .venv and install development dependencies."
        echo "No user data, global packages or existing environment are deleted."
        exit 0
    fi
    echo "Unknown option. Use --help." >&2
    exit 2
fi

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
venv_dir="$project_dir/.venv"
bootstrap_python="${PYTHON:-python3}"

if [[ ! -e "$venv_dir" ]]; then
    "$bootstrap_python" -m venv "$venv_dir"
fi
if [[ ! -f "$venv_dir/pyvenv.cfg" ]]; then
    echo "Refusing to use .venv without pyvenv.cfg; existing contents preserved." >&2
    exit 1
fi
if [[ -x "$venv_dir/bin/python" ]]; then
    venv_python="$venv_dir/bin/python"
elif [[ -x "$venv_dir/Scripts/python.exe" ]]; then
    venv_python="$venv_dir/Scripts/python.exe"
else
    echo "No Python interpreter in .venv; existing contents preserved." >&2
    exit 1
fi

# Never install into a system interpreter, even if .venv is malformed.
"$venv_python" -c 'import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)'
"$venv_python" -m pip install --editable "$project_dir[dev]"
echo "Development environment ready: $venv_dir"
echo "Run its Python/entry points directly or activate it in your current shell."
