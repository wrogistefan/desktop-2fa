"""Rasterize existing local SVG captures using a locally installed browser."""

import argparse
import math
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    for svg in sorted(args.directory.resolve().glob("*.svg")):
        root = ET.parse(svg).getroot()
        _, _, svg_width, svg_height = root.attrib["viewBox"].split()
        width = math.ceil(float(svg_width))
        height = math.ceil(float(svg_height))
        png = svg.with_suffix(".png")
        with tempfile.TemporaryDirectory(prefix="d2fa-render-") as temporary:
            wrapper = Path(temporary) / "capture.html"
            wrapper.write_text(
                '<html><body style="margin:0;background:#272822">'
                f'<img src="{svg.as_uri()}" width="{width}" height="{height}">'
                "</body></html>",
                encoding="utf-8",
            )
            subprocess.run(
                [
                    str(args.browser),
                    "--headless",
                    "--disable-gpu",
                    "--hide-scrollbars",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-background-networking",
                    "--allow-file-access-from-files",
                    f"--user-data-dir={Path(temporary) / 'profile'}",
                    f"--screenshot={png}",
                    f"--window-size={width},{height}",
                    wrapper.as_uri(),
                ],
                check=True,
                capture_output=True,
                timeout=60,
            )
        assert png.is_file() and png.stat().st_size > 1000
        print(f"{png.name}: {width} x {height}")


if __name__ == "__main__":
    main()
