"""Check installed CLI dependency compatibility without disclosing demo output.

Copy outside the checkout and run with the wheel environment's isolated Python.
"""

import importlib.metadata
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    import desktop_2fa

    assert Path(desktop_2fa.__file__).resolve().is_relative_to(Path(sys.prefix))
    version = importlib.metadata.version("desktop-2fa")
    assert version == desktop_2fa.__version__
    with tempfile.TemporaryDirectory(prefix="d2fa-cli-smoke-") as temporary:
        work = Path(temporary)
        password = work / "password.txt"
        password.write_text("synthetic-cli-dependency-password", encoding="utf-8")
        env = {**os.environ, "PYTHONUTF8": "1", "NO_COLOR": "1"}
        env.pop("PYTHONPATH", None)
        env.pop("DESKTOP_2FA_FORCE_INTERACTIVE", None)
        env["HOME"] = env["USERPROFILE"] = str(work)
        env["DESKTOP_2FA_VAULT"] = str(work / "vault.bin")

        def run(command: str, arguments: list[str]) -> str:
            executable = Path(sys.executable).parent / (
                command + (".exe" if os.name == "nt" else "")
            )
            result = subprocess.run(
                [str(executable), *arguments],
                cwd=work,
                env=env,
                input="",
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=60,
            )
            # Captured output can contain synthetic codes: never print it.
            if result.returncode:
                raise RuntimeError(f"Installed {command} failed ({result.returncode})")
            return result.stdout

        for command in ("d2fa", "desktop-2fa"):
            assert version in run(command, ["--version"])
            run(command, ["--help"])
            run(command, ["add", "--help"])
        base = [
            "--vault",
            str(work / "vault.bin"),
            "--password-file",
            str(password),
            "--allow-weak-passwords",
        ]
        run("d2fa", [*base, "vault", "init"])
        run("d2fa", [*base, "add", "synthetic", "Example", "JBSWY3DPEHPK3PXP"])
        assert "synthetic" in run("desktop-2fa", [*base, "list"])
        code = run("d2fa", [*base, "code", "synthetic", "--raw"]).strip()
        assert len(code) == 6 and code.isdecimal()
    print(
        json.dumps(
            {
                "python": sys.version.split()[0],
                "desktop-2fa": version,
                "typer": importlib.metadata.version("typer"),
                "click": importlib.metadata.version("click"),
                "result": "passed",
            }
        )
    )


if __name__ == "__main__":
    main()
