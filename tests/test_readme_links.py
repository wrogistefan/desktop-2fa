"""Keep the published package description independent of checkout/PyPI paths."""

import re
from pathlib import Path
from urllib.parse import urlsplit


def test_repository_readme_links_are_absolute_and_immutable() -> None:
    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text(encoding="utf-8")
    repository_links = []
    for target in re.findall(r"\]\(([^)]+)\)", readme):
        if target.startswith(("#", "mailto:")):
            continue
        url = urlsplit(target)
        assert url.scheme == "https" and url.netloc, target
        prefix = "/wrogistefan/desktop-2fa/"
        if url.netloc == "github.com" and url.path.startswith(prefix + "blob/"):
            relative = url.path.removeprefix(prefix + "blob/")
        elif url.netloc == "raw.githubusercontent.com" and url.path.startswith(prefix):
            relative = url.path.removeprefix(prefix)
        else:
            continue
        revision, file = relative.split("/", 1)
        assert re.fullmatch(r"[0-9a-f]{40}", revision), target
        assert (root / file).is_file(), target
        repository_links.append(target)
    assert repository_links
