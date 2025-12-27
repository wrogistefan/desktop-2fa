import os
from desktop_2fa.vault.vault import save_vault, load_vault
from desktop_2fa.vault.model import VaultData, TokenEntry

def test_vault_roundtrip(tmp_path):
    path = tmp_path / "vault.2fa"
    v = VaultData(version=1, entries=[TokenEntry(name="GitHub", secret="ABC", issuer="GitHub")])
    save_vault(str(path), v, "pass")
    v2 = load_vault(str(path), "pass")
    assert v2.entries[0].name == "GitHub"
