"""Run with an isolated wheel-installed interpreter from outside the checkout."""

import asyncio
import importlib
import importlib.metadata
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


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
    child_env = {**os.environ, "PYTHONUTF8": "1"}
    for command in ("d2fa", "desktop-2fa"):
        executable = scripts / (command + (".exe" if os.name == "nt" else ""))
        result = subprocess.run(
            [str(executable), "--version"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=child_env,
        )
        assert version in result.stdout
        subprocess.run(
            [str(executable), "--help"], check=True, capture_output=True, env=child_env
        )

    with tempfile.TemporaryDirectory(prefix="d2fa-smoke-") as directory:
        path = Path(directory) / "synthetic-vault"
        password = "synthetic-installed-wheel-password"
        vault = Vault()
        vault.add_entry("synthetic", "Example", "JBSWY3DPEHPK3PXP")
        vault.save(path, password, overwrite=False)
        loaded = Vault.load(path, password)
        assert loaded.data == vault.data
        new_password = "synthetic-changed-wheel-password"
        loaded.save(path, new_password)
        changed = Vault.load(path, new_password)
        assert changed.data == vault.data
        backup = Path(directory) / "synthetic-backup"
        export = Path(directory) / "synthetic-export"
        restored = Path(directory) / "synthetic-restored"
        changed.save(backup, new_password, overwrite=False)
        changed.save(export, new_password, overwrite=False)
        recovered = Vault.load(export, new_password)
        recovered.save(restored, new_password, overwrite=False)
        assert Vault.load(backup, new_password).data == vault.data
        assert Vault.load(restored, new_password).data == vault.data

        fixtures = Path(__file__).parent / "fixtures"
        if fixtures.is_dir():
            for fixture in json.loads(
                (fixtures / "manifest.json").read_text(encoding="utf-8")
            ):
                if fixture["supported"]:
                    historical = Vault.load(
                        fixtures / fixture["file"], fixture["password"]
                    )
                    assert historical.data.model_dump() == fixture["expected"]
                    historical_path = Path(directory) / fixture["file"]
                    historical.save(
                        historical_path, fixture["password"], overwrite=False
                    )
                    assert (
                        Vault.load(historical_path, fixture["password"]).data
                        == historical.data
                    )

        async def check_ui() -> None:
            app = D2FAApp(str(path), new_password, raise_load_errors=True)
            async with app.run_test() as pilot:
                await pilot.pause()
                assert app.query("#accounts")

        asyncio.run(check_ui())
    print("Installed wheel smoke checks passed.")


if __name__ == "__main__":
    main()
