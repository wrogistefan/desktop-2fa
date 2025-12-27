from pathlib import Path

from desktop_2fa.vault.model import TokenEntry, VaultData
from desktop_2fa.vault.vault import load_vault, save_vault


def test_vault_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "vault.2fa"
    v = VaultData(
        version=1, entries=[TokenEntry(name="GitHub", secret="ABC", issuer="GitHub")]
    )
    save_vault(str(path), v, "pass")
    v2 = load_vault(str(path), "pass")
    assert v2.entries[0].name == "GitHub"
