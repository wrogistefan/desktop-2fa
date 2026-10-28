"""Explicit fixture maintenance tool; never run as part of the test suite.

Run from the repository root with the development Python environment.
Only pinned historical source is executed; installed/current desktop_2fa is unused.
"""

import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
RELEASES = {
    "v0.5.0": "9cc8f643137df12b87484c9bb00caa4e40d16fd4",
    "v0.7.3": "55708399428820f2f01182d561ff0cf570e53d48",
    "v0.8.3": "cd8c3aeff9f192edf650a8b0f007a62da75224a2",
}
PASSWORD = "synthetic-żółw-compatibility-only"
ENTRIES = [
    dict(
        issuer="Synthetic SHA1",
        account_name="alice@example.invalid",
        secret=base64.b32encode(b"12345678901234567890").decode(),
        algorithm="SHA1",
        digits=6,
        period=30,
    ),
    dict(
        issuer="Synthetic SHA256",
        account_name="konto-żółw",
        secret=base64.b32encode(b"12345678901234567890123456789012").decode(),
        algorithm="SHA256",
        digits=8,
        period=45,
    ),
    dict(
        issuer="Synthetic SHA512",
        account_name=None,
        secret=base64.b32encode(
            b"1234567890123456789012345678901234567890123456789012345678901234"
        ).decode(),
        algorithm="SHA512",
        digits=7,
        period=60,
    ),
]


def main() -> None:
    manifest = []
    for release, commit in RELEASES.items():
        with tempfile.TemporaryDirectory(prefix="d2fa-historical-") as directory:
            root = Path(directory)
            files = [
                "__init__.py",
                "vault/__init__.py",
                "crypto/__init__.py",
                "vault/vault.py",
                "vault/models.py",
                "crypto/argon2.py",
                "crypto/aesgcm.py",
            ]
            for name in files:
                destination = root / "desktop_2fa" / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                # Empty package initializers avoid unrelated historical imports.
                source = (
                    b""
                    if name.endswith("__init__.py")
                    else subprocess.check_output(
                        ["git", "show", f"{commit}:src/desktop_2fa/{name}"], cwd=ROOT
                    )
                )
                destination.write_bytes(source)
            for empty in ([False, True] if release == "v0.8.3" else [False]):
                filename = f"{release}{'-empty-password' if empty else ''}.bin"
                password = "" if empty else PASSWORD
                script = root / "produce.py"
                script.write_text(
                    "from desktop_2fa.vault.vault import Vault\n"
                    "from desktop_2fa.vault.models import VaultData\n"
                    f"data = VaultData.model_validate_json({json.dumps({'version': 1, 'entries': ENTRIES})!r})\n"
                    f"Vault(data).save({str(OUTPUT / filename)!r}, {password!r})\n",
                    encoding="utf-8",
                )
                subprocess.run(
                    [sys.executable, str(script)],
                    cwd=root,
                    env={**os.environ, "PYTHONPATH": str(root)},
                    check=True,
                )
                manifest.append(
                    dict(
                        file=filename,
                        release=release,
                        commit=commit,
                        password=password,
                        supported=release != "v0.5.0" and not empty,
                        sha256=hashlib.sha256(
                            (OUTPUT / filename).read_bytes()
                        ).hexdigest(),
                        expected={"version": 1, "entries": ENTRIES},
                    )
                )
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
