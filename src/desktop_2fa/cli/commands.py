from desktop_2fa.vault import Vault
from desktop_2fa.totp.generator import generate as generate_totp

VAULT_PATH = "vault.json"  # później zrobimy config
PASSWORD = "password"  # później zrobimy config

def load_vault():
    return Vault.load(VAULT_PATH, PASSWORD)

def save_vault(vault):
    vault.save(VAULT_PATH, PASSWORD)

def list_entries():
    vault = load_vault()
    for entry in vault.entries:
        print(f"- {entry.issuer}")

def add_entry(issuer: str, secret: str):
    vault = load_vault()
    vault.add_entry(issuer=issuer, secret=secret)
    save_vault(vault)
    print(f"Added entry: {issuer}")

def generate_code(issuer: str):
    vault = load_vault()
    entry = vault.get_entry(issuer)
    code = generate_totp(entry.secret)
    print(code)
