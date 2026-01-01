"""CLI command implementations for Desktop 2FA."""

from __future__ import annotations

from pathlib import Path

import desktop_2fa.cli.helpers as helpers


def _path() -> Path:
    return Path(helpers.get_vault_path())


def list_entries(password: str) -> None:
    helpers.list_entries(_path(), password)


def add_entry(issuer: str, secret: str, password: str) -> None:
    helpers.add_entry(_path(), issuer, issuer, secret, password)


def generate_code(name: str, password: str) -> None:
    helpers.generate_code(_path(), name, password)


def remove_entry(name: str, password: str) -> None:
    helpers.remove_entry(_path(), name, password)


def rename_entry(old: str, new: str, password: str) -> None:
    helpers.rename_entry(_path(), old, new, password)


def export_vault(path: str, password: str) -> None:
    helpers.export_vault(_path(), Path(path), password)


def import_vault(path: str, password: str) -> None:
    helpers.import_vault(_path(), Path(path), password)


def backup_vault(password: str) -> None:
    backup_path = _path().with_suffix(".backup.bin")
    helpers.backup_vault(_path(), backup_path, password)
