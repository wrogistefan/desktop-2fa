"""Blocking UI operations. Call only in a worker, with synthetic data in tests."""

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from desktop_2fa import entry_service
from desktop_2fa.cli import helpers
from desktop_2fa.cli.commands import _get_backup_path
from desktop_2fa.vault import Vault
from desktop_2fa.vault.password_strength import evaluate_password_strength
from desktop_2fa.vault.vault import VaultConflict


class FormError(ValueError):
    """A static, safe message that may be displayed to the user."""


@dataclass
class Result:
    vault: Vault
    message: str


def check_new_password(values: dict[str, str], allow_weak: bool) -> str:
    password = values.get("new-password", "")
    if not password.strip():
        raise FormError("A non-empty new password is required.")
    if password != values.get("confirm-password"):
        raise FormError("New passwords do not match.")
    if not allow_weak:
        config = helpers.load_config()
        if evaluate_password_strength(password)["score"] < 3:
            if config.get("security", {}).get("reject_weak_passwords", False):
                raise FormError("Password too weak. Choose a stronger password.")
            if values.get("weak-password") != "yes":
                raise FormError(
                    "Password is weak. Choose a stronger one or confirm the weak-password checkbox."
                )
    return password


def perform(
    operation: str,
    path: Path,
    snapshot: Vault | None,
    index: int | None,
    values: dict[str, str],
    *,
    allow_weak: bool = False,
) -> Result:
    """Authenticate every operation; never mutate the displayed snapshot on failure.

    Mutations preserve the displayed revision, so an external edit is refused
    rather than applying a stale selection to a different entry.
    """
    password = values.get("password", "")
    force = values.get("overwrite") == "yes"
    if operation == "create":
        password = check_new_password(values, allow_weak)
        vault = Vault()
        vault.save(path, password, overwrite=force)
        return Result(vault, "Vault created.")
    if not password:
        raise FormError("A non-empty vault password is required.")
    if operation == "import":
        source = Path(values.get("file", "")).expanduser()
        if not values.get("file", "").strip():
            raise FormError("Enter the encrypted source file path.")
        # Apply the same alias/symlink protection as encrypted export.
        helpers.validate_export_destination(source, path, force=force)
        vault = Vault.load(source, password)
        vault.save(path, password, overwrite=force)
        return Result(vault, "Encrypted vault imported (replacement, not a merge).")

    authenticated = Vault.load(path, password)
    if operation == "unlock":
        message = "Vault unlocked."
        config = helpers.load_config()
        if config.get("security", {}).get("warn_on_weak_existing_passwords", False):
            if evaluate_password_strength(password)["score"] < 3:
                message += " Warning: your vault password is weak."
        return Result(authenticated, message)
    if snapshot is None:
        raise FormError("Unlock the vault first.")
    # Compare encrypted revisions, including changes that preserve entry data.
    if any(
        snapshot._revisions.get(key) != revision
        for key, revision in authenticated._revisions.items()
    ):
        raise VaultConflict(
            "Vault changed on disk. Lock and unlock it before retrying."
        )
    vault = deepcopy(snapshot)
    if operation == "add":
        uri = values.get("uri", "")
        if uri:
            if any(values.get(key) for key in ("name", "issuer", "secret")):
                raise FormError("Use either a provisioning URI or the manual fields.")
            parsed = entry_service.parse_otpauth_url(uri)
        else:
            if (
                not values.get("name", "").strip()
                or not values.get("issuer", "").strip()
            ):
                raise FormError("Account name and issuer are required.")
            parsed = entry_service.prepare_add(
                values["name"], values["issuer"], values.get("secret", "")
            )
        entry_service.add_prepared(vault, parsed)
    elif operation in {"rename", "remove"}:
        if index is None or not 0 <= index < len(vault.entries):
            raise FormError("Select an account first.")
        entry = vault.entries[index]
        if operation == "rename":
            name = values.get("name", "")
            if not name.strip():
                raise FormError("A new account name is required.")
            # An explicit list position also supports repairing legacy duplicates.
            vault.rename_entry(
                entry.account_name or entry.issuer or "", name, index=index + 1
            )
        else:
            if values.get("confirm") != "yes":
                raise FormError("Confirm permanent removal of the selected account.")
            # Exact row identity is explicit in the UI, including legacy duplicates.
            del vault.entries[index]
    elif operation == "change-password":
        password = check_new_password(values, allow_weak)
    elif operation in {"export", "backup"}:
        if operation == "backup":
            destination = _get_backup_path(path)
            force = False
        else:
            if not values.get("file", "").strip():
                raise FormError("Enter the encrypted destination file path.")
            destination = Path(values["file"]).expanduser()
            helpers.validate_export_destination(path, destination, force=force)
        vault.save(destination, password, overwrite=force)
        # Do not replace the session with a snapshot carrying export revisions.
        return Result(snapshot, f"Encrypted {operation} saved: {destination}")
    else:
        raise FormError("Unknown operation.")
    vault.save(path, password)
    return Result(
        vault,
        {
            "add": "Account added.",
            "rename": "Account renamed (name and issuer).",
            "remove": "Account removed.",
            "change-password": "Vault password changed.",
        }[operation],
    )
