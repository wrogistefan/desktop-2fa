"""Run with an isolated wheel-installed interpreter from outside the checkout."""

import asyncio
import importlib
import importlib.metadata
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def check_cli(executable: Path, option: str) -> str:
    result = subprocess.run(
        [str(executable), option],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"},
    )
    if result.returncode:
        raise RuntimeError(
            f"Installed CLI {executable.name} {option} failed ({result.returncode}):\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result.stdout


def main() -> None:
    import desktop_2fa
    from desktop_2fa.ui_textual.app import D2FAApp
    from desktop_2fa.vault import Vault

    package_path = Path(desktop_2fa.__file__).resolve()
    assert package_path.is_relative_to(
        Path(sys.prefix).resolve()
    ), "Package must be imported from the isolated installed environment"
    version = importlib.metadata.version("desktop-2fa")
    assert version == desktop_2fa.__version__
    for module in (
        "app.main",
        "app.clipboard",
        "app.config",
        "utils.time",
        "ui_textual.views.main_view",
        "cli.helpers",
        "cli.importers",
    ):
        importlib.import_module(f"desktop_2fa.{module}")
    assert (package_path.parent / "ui_textual" / "styles.css").is_file()

    scripts = Path(sys.executable).parent
    # Windows redirected help output needs UTF-8 for the documented Unicode text.
    for command in ("d2fa", "desktop-2fa"):
        executable = scripts / (command + (".exe" if os.name == "nt" else ""))
        assert version in check_cli(executable, "--version")
        check_cli(executable, "--help")

    with tempfile.TemporaryDirectory(prefix="d2fa-smoke-") as directory:
        path = Path(directory) / "synthetic-vault"
        password = "synthetic-installed-wheel-password"
        vault = Vault()
        vault.add_entry(
            name="synthetic",
            issuer="Example",
            secret="JBSWY3DPEHPK3PXP",
            algorithm="SHA256",
            digits=8,
            period=60,
        )
        vault.save(path, password, overwrite=False)
        loaded = Vault.load(path, password)
        assert loaded.data == vault.data

        async def check_ui() -> None:
            app = D2FAApp(str(path), password, raise_load_errors=True)
            async with app.run_test() as pilot:
                await pilot.pause()
                assert app.query("#accounts")

        asyncio.run(check_ui())
    print("Installed wheel smoke checks passed.")


if __name__ == "__main__":
    main()
