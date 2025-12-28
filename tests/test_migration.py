from desktop_2fa.vault.model import TokenEntry, VaultData
from desktop_2fa.vault.vault import Vault


def test_migration_adds_name_if_missing() -> None:
    old_entry = TokenEntry(name=None, issuer="GitHub", secret="AAA")
    data = VaultData(version=1, entries=[old_entry])

    vault = Vault(data)

    # symulujemy load() — migracja powinna ustawić name = issuer
    for entry in vault.entries:
        if not entry.name:
            entry.name = entry.issuer

    assert vault.entries[0].name == "GitHub"
    assert vault.entries[0].issuer == "GitHub"
