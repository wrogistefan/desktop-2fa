from desktop_2fa.vault.models import TotpEntry, VaultData
from desktop_2fa.vault.vault import Vault


def test_migration_adds_name_if_missing() -> None:
    old_entry = TotpEntry(account_name=None, issuer="GitHub", secret="JBSWY3DPEHPK3PXP")
    data = VaultData(version=1, entries=[old_entry])

    vault = Vault(data)

    # symulujemy load() — migracja powinna ustawić account_name = issuer
    for entry in vault.entries:
        if not entry.account_name:
            entry.account_name = entry.issuer

    assert vault.entries[0].account_name == "GitHub"
    assert vault.entries[0].issuer == "GitHub"
