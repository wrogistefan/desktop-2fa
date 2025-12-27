from desktop_2fa.totp.generator import generate as generate_totp
from desktop_2fa.vault import Vault

VAULT_PATH = "vault.json"  # później zrobimy config
PASSWORD = "password"  # później zrobimy config


def load_vault() -> Vault:
    return Vault.load(VAULT_PATH, PASSWORD)


def save_vault(vault: Vault) -> None:
    vault.save(VAULT_PATH, PASSWORD)


def list_entries() -> None:
    vault = load_vault()
    for entry in vault.entries:
        print(f"- {entry.issuer}")


def add_entry(issuer: str, secret: str) -> None:
    vault = load_vault()
    vault.add_entry(issuer=issuer, secret=secret)
    save_vault(vault)
    print(f"Added entry: {issuer}")


def generate_code(issuer: str) -> None:
    vault = load_vault()
    entry = vault.get_entry(issuer)
    code = generate_totp(entry.secret)
    print(code)
