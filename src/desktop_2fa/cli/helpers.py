import shutil
import time
from pathlib import Path

from desktop_2fa.vault import Vault


def list_entries() -> None:
    vault = load_vault()
    for entry in vault.entries:
        print(f"- {entry.name} ({entry.issuer})")


def add_entry(issuer: str, secret: str) -> None:
    vault = load_vault()
    vault.add_entry(name=issuer, issuer=issuer, secret=secret)
    save_vault(vault)
    print(f"Added entry: {issuer}")


def generate_code(issuer: str) -> None:
    vault = load_vault()
    entry = vault.get_entry(issuer)

    from desktop_2fa.totp import generate_totp

    code = generate_totp(entry.secret)

    print(code)


def remove_entry(issuer: str) -> None:
    vault = load_vault()
    vault.remove_entry(issuer)
    save_vault(vault)
    print(f"Removed entry: {issuer}")


def rename_entry(old_issuer: str, new_issuer: str) -> None:
    vault = load_vault()
    entry = vault.get_entry(old_issuer)
    entry.name = new_issuer
    entry.issuer = new_issuer
    save_vault(vault)
    print(f"Renamed '{old_issuer}' → '{new_issuer}'")


def export_vault(path: str) -> None:
    src = Path(get_vault_path())
    dst = Path(path)

    if not src.exists():
        print("Vault does not exist.")
        return

    shutil.copy2(src, dst)
    print(f"Exported vault to: {dst}")


def import_vault(path: str) -> None:
    src = Path(path)
    dst = Path(get_vault_path())

    if not src.exists():
        print("Source file does not exist.")
        return

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"Imported vault from: {src}")


def backup_vault() -> None:
    src = Path(get_vault_path())

    if not src.exists():
        print("Vault does not exist.")
        return

    backup_path = src.with_suffix(".backup.bin")
    shutil.copy2(src, backup_path)
    print(f"Backup created: {backup_path}")


def get_vault_path() -> str:
    return str(Path.home() / ".desktop-2fa" / "vault")


def load_vault() -> Vault:
    return Vault.load(get_vault_path())


def save_vault(vault: Vault) -> None:
    path = Path(get_vault_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    vault.save(str(path))


def timestamp() -> str:
    return str(int(time.time()))
