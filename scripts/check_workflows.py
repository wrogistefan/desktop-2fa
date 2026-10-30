"""Download pinned upstream actionlint, verify its checksum and validate YAML."""

import hashlib
import platform
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path
from urllib.request import urlopen


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    version = (root / ".github/actionlint-version").read_text().strip()
    system = {"Windows": "windows", "Linux": "linux", "Darwin": "darwin"}[
        platform.system()
    ]
    arch = {"AMD64": "amd64", "x86_64": "amd64", "arm64": "arm64", "aarch64": "arm64"}[
        platform.machine()
    ]
    extension = "zip" if system == "windows" else "tar.gz"
    name = f"actionlint_{version}_{system}_{arch}.{extension}"
    base = f"https://github.com/rhysd/actionlint/releases/download/v{version}"
    with urlopen(f"{base}/actionlint_{version}_checksums.txt", timeout=60) as response:
        checksums = response.read().decode()
    expected = next(
        line.split()[0] for line in checksums.splitlines() if line.split()[-1] == name
    )
    with urlopen(f"{base}/{name}", timeout=60) as response:
        payload = response.read()
    if hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError("actionlint checksum mismatch")
    with tempfile.TemporaryDirectory(prefix="d2fa-actionlint-") as directory:
        archive = Path(directory) / name
        archive.write_bytes(payload)
        binary = "actionlint.exe" if system == "windows" else "actionlint"
        target = Path(directory) / binary
        # Extract only the expected binary; never interpret archive paths.
        if extension == "zip":
            with zipfile.ZipFile(archive) as zipped:
                target.write_bytes(zipped.read(binary))
        else:
            with tarfile.open(archive) as tar:
                stream = tar.extractfile(binary)
                if stream is None:
                    raise ValueError("actionlint binary missing")
                with stream:
                    target.write_bytes(stream.read())
        target.chmod(0o755)
        subprocess.run([str(target)], cwd=root, check=True)


if __name__ == "__main__":
    main()
