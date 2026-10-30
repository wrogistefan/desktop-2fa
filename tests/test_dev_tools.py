"""Development tooling must preserve synthetic user data and local environments."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASH = "C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else shutil.which("bash")


@pytest.mark.skipif(not BASH or not Path(BASH).is_file(), reason="Bash unavailable")
@pytest.mark.parametrize("existing", [False, True])
def test_reset_preserves_user_data_and_only_installs_in_project_environment(
    tmp_path: Path, existing: bool
) -> None:
    project = tmp_path / "project with spaces"
    project.mkdir()
    script = project / "dev-reset.sh"
    shutil.copyfile(ROOT / "dev-reset.sh", script)
    home = tmp_path / "synthetic-home"
    sentinel = home / ".config/desktop-2fa/synthetic-vault"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_bytes(b"synthetic-user-data")
    global_package = home / ".local/lib/python3/site-packages/desktop_2fa/sentinel"
    global_package.parent.mkdir(parents=True)
    global_package.write_bytes(b"synthetic-global-package")
    calls = tmp_path / "calls"
    bootstrap = tmp_path / "bootstrap"
    bootstrap.write_text(
        "#!/usr/bin/env bash\nset -eu\n"
        'printf "bootstrap:%s\\n" "$*" >> "$TEST_CALLS"\n'
        '[[ "$1" == "-m" && "$2" == "venv" ]]\n'
        'mkdir -p "$3/bin"\n'
        'touch "$3/pyvenv.cfg"\n'
        'cp "$TEST_INTERPRETER" "$3/bin/python"\n'
        'chmod +x "$3/bin/python"\n',
        encoding="utf-8",
        newline="\n",
    )
    interpreter = tmp_path / "interpreter"
    interpreter.write_text(
        "#!/usr/bin/env bash\nset -eu\n" 'printf "venv:%s\\n" "$*" >> "$TEST_CALLS"\n',
        encoding="utf-8",
        newline="\n",
    )
    bootstrap.chmod(0o755)
    if existing:
        venv = project / ".venv"
        (venv / "bin").mkdir(parents=True)
        (venv / "pyvenv.cfg").touch()
        shutil.copyfile(interpreter, venv / "bin/python")
        (venv / "bin/python").chmod(0o755)
        (venv / "sentinel").write_bytes(b"synthetic-existing-environment")
    env = {
        **os.environ,
        "HOME": home.as_posix(),
        "PYTHON": bootstrap.as_posix(),
        "TEST_CALLS": calls.as_posix(),
        "TEST_INTERPRETER": interpreter.as_posix(),
    }
    subprocess.run([str(BASH), str(script)], env=env, check=True, capture_output=True)
    assert sentinel.read_bytes() == b"synthetic-user-data"
    assert global_package.read_bytes() == b"synthetic-global-package"
    text = calls.read_text(encoding="utf-8")
    assert "venv:-c import sys" in text
    assert "venv:-m pip install --editable " in text
    assert "project with spaces[dev]" in text
    assert "--break-system-packages" not in text
    assert ("bootstrap:" in text) is not existing
    if existing:
        assert (
            project / ".venv/sentinel"
        ).read_bytes() == b"synthetic-existing-environment"


@pytest.mark.skipif(not BASH or not Path(BASH).is_file(), reason="Bash unavailable")
def test_reset_refuses_malformed_environment_without_touching_it(
    tmp_path: Path,
) -> None:
    script = tmp_path / "dev-reset.sh"
    shutil.copyfile(ROOT / "dev-reset.sh", script)
    venv = tmp_path / ".venv"
    venv.mkdir()
    sentinel = venv / "sentinel"
    sentinel.write_bytes(b"synthetic-existing-data")
    result = subprocess.run([str(BASH), str(script)], capture_output=True)
    assert result.returncode == 1
    assert sentinel.read_bytes() == b"synthetic-existing-data"


@pytest.mark.skipif(not shutil.which("make"), reason="GNU make unavailable")
def test_make_dry_runs_all_supported_targets() -> None:
    result = subprocess.run(
        [
            "make",
            "-n",
            "test",
            "test-cov",
            "test-cov-html",
            "lint",
            "lint-fix",
            "format",
            "format-check",
            "typecheck",
            "check-all",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "-m mypy src" in result.stdout
    assert "-m black --check ." in result.stdout
