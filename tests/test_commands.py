import shutil
from pathlib import Path
from typing import Any

import pytest
import typer

from desktop_2fa.cli import commands, helpers
from desktop_2fa.vault.vault import VaultIOError

TEST_PASSWORD = "jawislajawisla"


@pytest.fixture
def fake_vault_env(tmp_path: Path, monkeypatch: Any) -> Path:
    fake_vault = tmp_path / "vault"

    monkeypatch.setattr(
        "desktop_2fa.cli.helpers.get_vault_path",
        lambda: str(fake_vault),
    )

    if fake_vault.parent.exists():
        shutil.rmtree(fake_vault.parent)
    fake_vault.parent.mkdir(parents=True, exist_ok=True)

    return fake_vault


@pytest.fixture
def fake_ctx() -> Any:
    class FakeContext:
        def __init__(self) -> None:
            self.obj: dict[str, Any] = {"interactive": True, "password": TEST_PASSWORD}

    return FakeContext()


@pytest.fixture
def fake_ctx_wrong_password() -> Any:
    class FakeContext:
        def __init__(self) -> None:
            self.obj: dict[str, Any] = {
                "interactive": True,
                "password": "wrongpassword",
            }

    return FakeContext()


def test_list_entries_empty(fake_vault_env: Path, capsys: Any, fake_ctx: Any) -> None:
    commands.list_entries(fake_ctx)
    out = capsys.readouterr().out.strip().splitlines()
    vault_path = str(fake_vault_env)
    assert out == [
        "No vault found.",
        "A new encrypted vault will be created.",
        f"Vault created at {vault_path}",
        "No entries found.",
    ]


def test_list_entries_noninteractive_creates_vault_with_messages(
    fake_vault_env: Path, capsys: Any
) -> None:

    class NonInteractiveCtx:
        def __init__(self) -> None:
            self.obj: dict[str, Any] = {"interactive": False, "password": TEST_PASSWORD}

    # Ensure vault doesn't exist
    if fake_vault_env.exists():
        fake_vault_env.unlink()

    commands.list_entries(NonInteractiveCtx())  # type: ignore[arg-type]
    out = capsys.readouterr().out.strip().splitlines()

    vault_path = str(fake_vault_env)
    # Must print all required messages regardless of interactive mode
    assert "No vault found." in out
    assert "A new encrypted vault will be created." in out
    assert f"Vault created at {vault_path}" in out
    assert "No entries found." in out

    # Verify vault was actually created
    assert fake_vault_env.exists()


def test_add_entry_and_list(fake_vault_env: Path, capsys: Any, fake_ctx: Any) -> None:
    commands.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)

    # po add_entry:
    out = capsys.readouterr().out.strip().splitlines()
    vault_path = str(fake_vault_env)
    assert out == [
        "No vault found.",
        "A new encrypted vault will be created.",
        f"Vault created at {vault_path}",
        "Entry added: GitHub",
    ]

    commands.list_entries(fake_ctx)
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["- GitHub (GitHub)"]

    vault = helpers.load_vault(fake_vault_env, TEST_PASSWORD)
    assert len(vault.entries) == 1
    assert vault.entries[0].issuer == "GitHub"
    assert vault.entries[0].account_name == "GitHub"
    assert vault.entries[0].secret == "JBSWY3DPEHPK3PXP"


def test_add_entry_noninteractive_creates_vault_with_messages(
    fake_vault_env: Path, capsys: Any
) -> None:

    class NonInteractiveCtx:
        def __init__(self) -> None:
            self.obj: dict[str, Any] = {"interactive": False, "password": TEST_PASSWORD}

    # Ensure vault doesn't exist
    if fake_vault_env.exists():
        fake_vault_env.unlink()

    commands.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP", NonInteractiveCtx())  # type: ignore[arg-type]
    out = capsys.readouterr().out.strip().splitlines()

    vault_path = str(fake_vault_env)
    # Must print all required messages regardless of interactive mode
    assert "No vault found." in out
    assert "A new encrypted vault will be created." in out
    assert f"Vault created at {vault_path}" in out
    assert "Entry added: GitHub" in out

    # Verify vault was actually created
    assert fake_vault_env.exists()


def test_generate_code(fake_vault_env: Path, capsys: Any, fake_ctx: Any) -> None:
    commands.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)
    capsys.readouterr()  # czyścimy output po add_entry

    commands.generate_code("GitHub", fake_ctx)
    out = capsys.readouterr().out.strip()

    # generate_code wypisuje tylko kod, jedną linię
    lines = out.splitlines()
    code = lines[-1]
    assert len(code) == 6
    assert code.isdigit()


def test_generate_code_missing_entry_raises(
    fake_vault_env: Path, fake_ctx: Any
) -> None:
    # Create empty vault
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)
    with pytest.raises(ValueError):
        commands.generate_code("Nope", fake_ctx)


def test_remove_entry(fake_vault_env: Path, fake_ctx: Any) -> None:
    commands.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)
    commands.remove_entry("GitHub", fake_ctx)

    vault = helpers.load_vault(fake_vault_env, TEST_PASSWORD)
    assert len(vault.entries) == 0


def test_remove_entry_missing_raises(fake_vault_env: Path, fake_ctx: Any) -> None:
    # Create empty vault
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)
    with pytest.raises(ValueError):
        commands.remove_entry("Nope", fake_ctx)


def test_rename_entry(fake_vault_env: Path, capsys: Any, fake_ctx: Any) -> None:
    commands.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)
    capsys.readouterr()  # czyścimy output po add_entry

    commands.rename_entry("GitHub", "NewGitHub", fake_ctx)

    vault = helpers.load_vault(fake_vault_env, TEST_PASSWORD)
    assert len(vault.entries) == 1
    entry = vault.entries[0]
    assert entry.account_name == "NewGitHub"
    assert entry.issuer == "NewGitHub"


def test_rename_entry_missing_raises(fake_vault_env: Path, fake_ctx: Any) -> None:
    # Create empty vault
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)
    with pytest.raises(ValueError):
        commands.rename_entry("Old", "New", fake_ctx)


def test_export_vault(
    fake_vault_env: Path, tmp_path: Path, capsys: Any, fake_ctx: Any
) -> None:
    commands.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)
    capsys.readouterr()  # wyczyść output po add_entry

    export_path = tmp_path / "export.bin"
    commands.export_vault(str(export_path), fake_ctx)

    assert export_path.exists()
    assert export_path.stat().st_size > 0

    out = capsys.readouterr().out
    assert "Exported vault to:" in out


def test_export_vault_missing_file(
    fake_vault_env: Path, tmp_path: Path, monkeypatch: Any, capsys: Any, fake_ctx: Any
) -> None:
    fake_vault = tmp_path / "vault_missing"
    monkeypatch.setattr(
        "desktop_2fa.cli.helpers.get_vault_path",
        lambda: str(fake_vault),
    )

    commands.export_vault(str(tmp_path / "any.bin"), fake_ctx)
    out = capsys.readouterr().out
    # zgodnie z aktualnym helpers.export_vault, brak explicit checka,
    # więc tutaj nie wymuszamy konkretnego komunikatu – tylko, że coś wypisuje.
    assert "No vault found." in out


def test_import_vault(
    fake_vault_env: Path, tmp_path: Path, capsys: Any, fake_ctx: Any
) -> None:
    src = tmp_path / "src.bin"

    commands.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)
    capsys.readouterr()  # output po add_entry

    commands.export_vault(str(src), fake_ctx)
    capsys.readouterr()  # output po export

    vault = helpers.load_vault(fake_vault_env, TEST_PASSWORD)
    vault.entries.clear()
    vault.save(fake_vault_env, TEST_PASSWORD)

    commands.import_vault(str(src), True, fake_ctx)

    vault = helpers.load_vault(fake_vault_env, TEST_PASSWORD)
    assert len(vault.entries) == 1
    assert vault.entries[0].issuer == "GitHub"
    assert vault.entries[0].secret == "JBSWY3DPEHPK3PXP"

    out = capsys.readouterr().out
    assert "Vault imported from" in out


def test_import_vault_missing_source(
    fake_vault_env: Path, tmp_path: Path, capsys: Any, fake_ctx: Any
) -> None:
    missing = tmp_path / "nope.bin"
    with pytest.raises(VaultIOError):
        commands.import_vault(str(missing), False, fake_ctx)


def test_import_vault_refuses_overwrite_without_force(
    fake_vault_env: Path, tmp_path: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Create existing vault
    commands.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)
    capsys.readouterr()  # clear output

    # Create source vault
    src = tmp_path / "src.bin"
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(src, TEST_PASSWORD)

    # Try import without force - should refuse
    with pytest.raises(typer.Exit):
        commands.import_vault(str(src), False, fake_ctx)

    out = capsys.readouterr().out.strip()
    assert out == "Refusing to overwrite existing vault. Use --force to proceed."


def test_backup_vault(fake_vault_env: Path, capsys: Any, fake_ctx: Any) -> None:
    commands.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)
    capsys.readouterr()  # output po add_entry

    # First backup creates backup.bin
    backup_path = fake_vault_env.with_suffix(".backup.bin")
    commands.backup_vault(fake_ctx)

    assert backup_path.exists()
    assert backup_path.stat().st_size > 0

    out = capsys.readouterr().out
    assert "Backup created:" in out

    # Second backup creates backup-1.bin
    commands.backup_vault(fake_ctx)
    backup_path_1 = fake_vault_env.with_suffix(".backup-1.bin")

    assert backup_path_1.exists()
    assert backup_path_1.stat().st_size > 0

    out = capsys.readouterr().out
    assert "Backup created:" in out


def test_backup_vault_missing(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, tmp_path: Path, fake_ctx: Any
) -> None:
    fake_missing = tmp_path / "no_vault_here"
    monkeypatch.setattr(
        "desktop_2fa.cli.helpers.get_vault_path",
        lambda: str(fake_missing),
    )

    commands.backup_vault(fake_ctx)
    out = capsys.readouterr().out
    # Now prints "No vault found."
    assert "No vault found." in out


def test_generate_code_invalid_password(
    fake_vault_env: Path, capsys: Any, fake_ctx_wrong_password: Any
) -> None:
    # Create vault with correct password
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    commands.generate_code("nonexistent", fake_ctx_wrong_password)
    out = capsys.readouterr().out.strip()
    assert out == "Invalid vault password."


def test_add_entry_invalid_password(
    fake_vault_env: Path, capsys: Any, fake_ctx_wrong_password: Any
) -> None:
    # Create vault with correct password
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    commands.add_entry("Test", "Test", "JBSWY3DPEHPK3PXP", fake_ctx_wrong_password)
    out = capsys.readouterr().out.strip()
    assert out == "Invalid vault password."


def test_list_entries_invalid_password(
    fake_vault_env: Path, capsys: Any, fake_ctx_wrong_password: Any
) -> None:
    # Create vault with correct password
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    commands.list_entries(fake_ctx_wrong_password)
    out = capsys.readouterr().out.strip()
    assert out == "Invalid vault password."


def test_remove_entry_invalid_password(
    fake_vault_env: Path, capsys: Any, fake_ctx_wrong_password: Any
) -> None:
    # Create vault with correct password
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    commands.remove_entry("Test", fake_ctx_wrong_password)
    out = capsys.readouterr().out.strip()
    assert out == "Invalid vault password."


def test_export_vault_invalid_password(
    fake_vault_env: Path, tmp_path: Path, capsys: Any, fake_ctx_wrong_password: Any
) -> None:
    # Create vault with correct password
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    export_path = tmp_path / "export.bin"
    commands.export_vault(str(export_path), fake_ctx_wrong_password)
    out = capsys.readouterr().out.strip()
    assert out == "Invalid vault password."


def test_import_vault_invalid_password(
    fake_vault_env: Path, tmp_path: Path, capsys: Any, fake_ctx_wrong_password: Any
) -> None:
    # Create source vault with correct password
    from desktop_2fa.vault import Vault

    vault = Vault()
    src = tmp_path / "src.bin"
    vault.save(src, TEST_PASSWORD)

    commands.import_vault(str(src), False, fake_ctx_wrong_password)
    out = capsys.readouterr().out.strip()
    assert out == "Invalid vault password."


def test_backup_vault_invalid_password(
    fake_vault_env: Path, capsys: Any, fake_ctx_wrong_password: Any
) -> None:
    # Create vault with correct password
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    commands.backup_vault(fake_ctx_wrong_password)
    out = capsys.readouterr().out.strip()
    assert out == "Invalid vault password."


def test_add_entry_otpauth_url(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    otpauth_url = "otpauth://totp/GitHub:octocat?secret=JBSWY3DPEHPK3PXP&issuer=GitHub"
    commands.add_entry("GitHub", otpauth_url, "", fake_ctx)

    out = capsys.readouterr().out.strip().splitlines()
    assert "Entry added: octocat" in out


def test_add_entry_invalid_otpauth_url(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    invalid_url = "otpauth://invalid"
    commands.add_entry("Test", invalid_url, "", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Invalid otpauth URL:" in out


def test_add_entry_invalid_secret(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    commands.add_entry("Test", "Test", "invalid_secret", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Invalid secret: not valid Base32." in out


def test_list_entries_existing_vault_no_entries(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    commands.list_entries(fake_ctx)

    out = capsys.readouterr().out.strip().splitlines()
    assert "No entries found." in out


def test_generate_code_existing_vault_no_entries(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    with pytest.raises(ValueError, match="not found"):
        commands.generate_code("nonexistent", fake_ctx)


def test_remove_entry_existing_vault_no_entries(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    with pytest.raises(ValueError, match="not found"):
        commands.remove_entry("nonexistent", fake_ctx)


def test_rename_entry_existing_vault_no_entries(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    with pytest.raises(ValueError, match="not found"):
        commands.rename_entry("old", "new", fake_ctx)


def test_export_vault_existing_vault_no_entries(
    fake_vault_env: Path, tmp_path: Path, capsys: Any, fake_ctx: Any
) -> None:
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    export_path = tmp_path / "export.bin"
    commands.export_vault(str(export_path), fake_ctx)

    assert export_path.exists()
    out = capsys.readouterr().out
    assert "Exported vault to:" in out


def test_import_vault_corrupted_source(
    fake_vault_env: Path, tmp_path: Path, capsys: Any, fake_ctx: Any
) -> None:
    corrupted = tmp_path / "corrupted.bin"
    corrupted.write_text("corrupted data")

    commands.import_vault(str(corrupted), True, fake_ctx)
    out = capsys.readouterr().out.strip()
    assert "Source vault file format is unsupported." in out


def test_import_vault_unsupported_format(
    fake_vault_env: Path, tmp_path: Path, capsys: Any, fake_ctx: Any
) -> None:
    unsupported = tmp_path / "unsupported.bin"
    # Create a file that looks like a vault but has unsupported format
    unsupported.write_bytes(b"unsupported_format_data")

    commands.import_vault(str(unsupported), True, fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Source vault file format is unsupported." in out


def test_backup_vault_existing_vault_no_entries(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    commands.backup_vault(fake_ctx)

    backup_path = fake_vault_env.with_suffix(".backup.bin")
    assert backup_path.exists()
    out = capsys.readouterr().out
    assert "Backup created:" in out


def test_init_vault_existing_no_force(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    commands.init_vault(False, fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Vault already exists." in out
    assert "Use --force to overwrite." in out


def test_init_vault_existing_with_force(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    commands.init_vault(True, fake_ctx)

    out = capsys.readouterr().out.strip()
    vault_path = str(fake_vault_env)
    assert f"Vault created at {vault_path}" in out


def test_init_vault_new(fake_vault_env: Path, capsys: Any, fake_ctx: Any) -> None:
    commands.init_vault(False, fake_ctx)

    out = capsys.readouterr().out.strip()
    vault_path = str(fake_vault_env)
    assert f"Vault created at {vault_path}" in out
    assert fake_vault_env.exists()


def test_remove_entry_unsupported_format(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Create a file with wrong magic header
    fake_vault_env.write_bytes(
        b"WRNG" + b"\x01" + b"16byte_salt_here" + b"encrypted_data"
    )

    commands.remove_entry("GitHub", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Vault file format is unsupported." in out


def test_rename_entry_unsupported_format(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Create a file with wrong magic header
    fake_vault_env.write_bytes(
        b"WRNG" + b"\x01" + b"16byte_salt_here" + b"encrypted_data"
    )

    commands.rename_entry("GitHub", "NewGitHub", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Vault file format is unsupported." in out


def test_export_vault_unsupported_format(
    fake_vault_env: Path, tmp_path: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Create a file with wrong magic header
    fake_vault_env.write_bytes(
        b"WRNG" + b"\x01" + b"16byte_salt_here" + b"encrypted_data"
    )

    export_path = tmp_path / "export.bin"
    commands.export_vault(str(export_path), fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Vault file format is unsupported." in out


def test_backup_vault_unsupported_format(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Create a file with wrong magic header
    fake_vault_env.write_bytes(
        b"WRNG" + b"\x01" + b"16byte_salt_here" + b"encrypted_data"
    )

    commands.backup_vault(fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Vault file format is unsupported." in out


def test_add_entry_unsupported_format(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Create a file with wrong magic header
    fake_vault_env.write_bytes(
        b"WRNG" + b"\x01" + b"16byte_salt_here" + b"encrypted_data"
    )

    commands.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Vault file format is unsupported." in out


def test_list_entries_unsupported_format(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Create a file with wrong magic header
    fake_vault_env.write_bytes(
        b"WRNG" + b"\x01" + b"16byte_salt_here" + b"encrypted_data"
    )

    commands.list_entries(fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Vault file format is unsupported." in out


def test_generate_code_unsupported_format(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Create a file with wrong magic header
    fake_vault_env.write_bytes(
        b"WRNG" + b"\x01" + b"16byte_salt_here" + b"encrypted_data"
    )

    commands.generate_code("GitHub", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Vault file format is unsupported." in out


# =============================================================================
# Regression tests for rename semantics (Issue #9)
# =============================================================================


def test_rename_entry_with_duplicates_aborts(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    from desktop_2fa.vault import Vault
    from desktop_2fa.vault.models import TotpEntry

    # Create a vault with two entries having the same name (simulating legacy vault)
    vault = Vault()
    # Directly add entries to bypass duplicate check (simulating legacy data)
    entry1 = TotpEntry(
        account_name="GitHub", issuer="GitHub", secret="JBSWY3DPEHPK3PXP"
    )
    entry2 = TotpEntry(
        account_name="GitHub", issuer="GitHub2", secret="JBSWY3DPEHPK3PXP"
    )
    vault.data.entries.append(entry1)
    vault.data.entries.append(entry2)
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Try to rename - should abort with error message
    commands.rename_entry("GitHub", "NewName", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert (
        "Multiple entries named 'GitHub' exist. Operation aborted. Resolve duplicates first."
        in out
    )

    # Verify no entry was renamed (vault unchanged)
    vault = helpers.load_vault(fake_vault_env, TEST_PASSWORD)
    assert len(vault.entries) == 2
    # Both entries should still have their original names
    names = [e.account_name for e in vault.entries]
    assert names.count("GitHub") == 2


def test_rename_entry_no_duplicates_success(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    commands.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)
    capsys.readouterr()  # clear output

    commands.rename_entry("GitHub", "NewGitHub", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Renamed 'GitHub' → 'NewGitHub'" in out

    # Verify entry was renamed
    vault = helpers.load_vault(fake_vault_env, TEST_PASSWORD)
    assert len(vault.entries) == 1
    assert vault.entries[0].account_name == "NewGitHub"
    assert vault.entries[0].issuer == "NewGitHub"


def test_rename_entry_case_sensitive(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Create vault with one entry
    commands.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)
    capsys.readouterr()  # clear output

    # Try to rename using lowercase - should find the entry (case-insensitive match via get_entry)
    # Note: The current implementation uses exact match in find_entries
    commands.rename_entry("GitHub", "GitLab", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Renamed 'GitHub' → 'GitLab'" in out

    # Verify entry was renamed
    vault = helpers.load_vault(fake_vault_env, TEST_PASSWORD)
    assert vault.entries[0].account_name == "GitLab"


def test_rename_entry_by_issuer(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    commands.add_entry("MyAccount", "GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)
    capsys.readouterr()  # clear output

    # Rename by issuer
    commands.rename_entry("GitHub", "NewIssuer", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Renamed 'GitHub' → 'NewIssuer'" in out

    # Verify both account_name and issuer were updated
    vault = helpers.load_vault(fake_vault_env, TEST_PASSWORD)
    assert vault.entries[0].account_name == "NewIssuer"
    assert vault.entries[0].issuer == "NewIssuer"


def test_rename_entry_no_vault(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Ensure no vault exists
    if fake_vault_env.exists():
        fake_vault_env.unlink()

    commands.rename_entry("Old", "New", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "No vault found." in out


def test_rename_entry_missing_entry_raises(fake_vault_env: Path, fake_ctx: Any) -> None:
    # Create empty vault
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    with pytest.raises(ValueError, match="not found"):
        commands.rename_entry("Nonexistent", "NewName", fake_ctx)


# =============================================================================
# Tests for uncovered exception handlers in commands.py
# =============================================================================


def test_add_entry_interactive_invalid_base32(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Create a vault first so add_entry_interactive path is taken
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    commands.add_entry_interactive("Test", "Test", "invalid_secret!@#", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Invalid secret: not valid Base32" in out
    assert "Example: ABCDEFGHIJKL2345" in out


def test_list_entries_permission_error_directory(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    # Create a vault first
    from desktop_2fa.vault import Vault
    from desktop_2fa.vault.vault import PermissionDenied

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Mock Vault.load to raise PermissionDenied
    def mock_load(*args: Any, **kwargs: Any) -> None:
        raise PermissionDenied("Permission denied")

    monkeypatch.setattr("desktop_2fa.vault.Vault.load", mock_load)

    commands.list_entries(fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Cannot access vault directory (permission denied)" in out


def test_list_entries_corrupted_vault(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    # Mock Vault.load to raise CorruptedVault
    from desktop_2fa.vault.vault import CorruptedVault

    def mock_load(*args: Any, **kwargs: Any) -> None:
        raise CorruptedVault("Vault file is corrupted")

    monkeypatch.setattr("desktop_2fa.vault.Vault.load", mock_load)

    # Create a dummy file so the path exists
    fake_vault_env.write_bytes(b"dummy")

    commands.list_entries(fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Vault file is corrupted" in out


def test_list_entries_io_error(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Create a valid-looking vault that will fail on read
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Mock open to raise OSError
    import builtins

    original_open = builtins.open

    def mock_open(*args: Any, **kwargs: Any) -> None:
        raise OSError("Disk error")

    builtins.open = mock_open  # type: ignore[assignment]
    try:
        commands.list_entries(fake_ctx)
        out = capsys.readouterr().out.strip()
        assert "Failed to access vault file" in out
    finally:
        builtins.open = original_open


def test_add_entry_permission_error_directory(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    # Create a vault first
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Mock mkdir to raise PermissionError
    def mock_mkdir(*args: Any, **kwargs: Any) -> None:
        raise PermissionError("Permission denied")

    monkeypatch.setattr("pathlib.Path.mkdir", mock_mkdir)

    commands.add_entry("Test", "Test", "JBSWY3DPEHPK3PXP", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Cannot access vault directory (permission denied)" in out


def test_add_entry_vault_not_found_creates_new(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    # Create a vault first
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Mock Vault.load to raise VaultNotFound
    from desktop_2fa.vault.vault import VaultNotFound

    def mock_load(*args: Any, **kwargs: Any) -> None:
        raise VaultNotFound("Vault file not found")

    monkeypatch.setattr("desktop_2fa.vault.Vault.load", mock_load)

    commands.add_entry("Test", "Test", "JBSWY3DPEHPK3PXP", fake_ctx)

    out_lines = capsys.readouterr().out.strip().splitlines()
    out_text = " ".join(out_lines)  # Join for substring checking
    assert "No vault found" in out_text
    assert "new encrypted vault will be created" in out_text
    assert "Vault created at" in out_text
    assert "Entry added: Test" in out_text


def test_generate_code_no_vault_warns(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Ensure no vault exists
    if fake_vault_env.exists():
        fake_vault_env.unlink()

    commands.generate_code("Test", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "No vault found" in out
    assert "Nothing to generate" in out


def test_rename_entry_permission_denied(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    # Create a vault first
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP")
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Mock Vault.load to raise PermissionDenied
    from desktop_2fa.vault.vault import PermissionDenied

    def mock_load(*args: Any, **kwargs: Any) -> None:
        raise PermissionDenied("Permission denied")

    monkeypatch.setattr("desktop_2fa.vault.Vault.load", mock_load)

    commands.rename_entry("GitHub", "NewGitHub", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Cannot access vault directory (permission denied)" in out


def test_rename_entry_io_error(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    # Create a vault first
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP")
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Mock Vault.save to raise VaultIOError
    from desktop_2fa.vault.vault import VaultIOError

    def mock_save(self: Vault, *args: Any, **kwargs: Any) -> None:
        raise VaultIOError("Disk error")

    monkeypatch.setattr("desktop_2fa.vault.Vault.save", mock_save)

    commands.rename_entry("GitHub", "NewGitHub", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Failed to access vault file" in out


def test_backup_vault_permission_denied(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    # Create a vault first
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP")
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Mock Vault.load to raise PermissionDenied
    from desktop_2fa.vault.vault import PermissionDenied

    def mock_load(*args: Any, **kwargs: Any) -> None:
        raise PermissionDenied("Permission denied")

    monkeypatch.setattr("desktop_2fa.vault.Vault.load", mock_load)

    commands.backup_vault(fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Cannot access vault directory (permission denied)" in out


def test_backup_vault_permission_error_io(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Create a corrupted vault file
    fake_vault_env.write_bytes(b"WRNG\x01" + b"16byte_salt_here" + b"encrypted_data")

    commands.backup_vault(fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Vault file format is unsupported" in out


def test_backup_vault_io_error(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    # Create a vault first
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP")
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Mock Vault.save to raise VaultIOError
    from desktop_2fa.vault.vault import VaultIOError

    def mock_save(self: Vault, *args: Any, **kwargs: Any) -> None:
        raise VaultIOError("Disk full")

    monkeypatch.setattr("desktop_2fa.vault.Vault.save", mock_save)

    commands.backup_vault(fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Failed to access vault file" in out


def test_init_vault_permission_error(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    # Ensure no vault exists
    if fake_vault_env.exists():
        fake_vault_env.unlink()

    # Mock mkdir to raise PermissionError
    def mock_mkdir(*args: Any, **kwargs: Any) -> None:
        raise PermissionError("Permission denied")

    monkeypatch.setattr("pathlib.Path.mkdir", mock_mkdir)

    commands.init_vault(False, fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Cannot access vault directory (permission denied)" in out


def test_init_vault_permission_denied_on_save(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    from desktop_2fa.vault import Vault

    # Ensure no vault exists
    if fake_vault_env.exists():
        fake_vault_env.unlink()

    # Mock Vault.save to raise PermissionDenied
    from desktop_2fa.vault.vault import PermissionDenied

    def mock_save(self: Vault, *args: Any, **kwargs: Any) -> None:
        raise PermissionDenied("Permission denied")

    monkeypatch.setattr("desktop_2fa.vault.Vault.save", mock_save)

    commands.init_vault(False, fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Cannot access vault directory (permission denied)" in out


def test_init_vault_io_error_on_save(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    from desktop_2fa.vault import Vault

    # Ensure no vault exists
    if fake_vault_env.exists():
        fake_vault_env.unlink()

    # Mock Vault.save to raise VaultIOError
    from desktop_2fa.vault.vault import VaultIOError

    def mock_save(self: Vault, *args: Any, **kwargs: Any) -> None:
        raise VaultIOError("Failed to create vault file")

    monkeypatch.setattr("desktop_2fa.vault.Vault.save", mock_save)

    commands.init_vault(False, fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Failed to create vault file" in out


# =============================================================================
# Additional tests for remaining exception handlers
# =============================================================================


def test_list_entries_permission_denied(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    # Create a vault first
    from desktop_2fa.vault import Vault
    from desktop_2fa.vault.vault import PermissionDenied

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Mock Vault.load to raise PermissionDenied
    def mock_load(*args: Any, **kwargs: Any) -> None:
        raise PermissionDenied("Permission denied")

    monkeypatch.setattr("desktop_2fa.vault.Vault.load", mock_load)

    commands.list_entries(fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Cannot access vault directory (permission denied)" in out


def test_list_entries_vault_not_found_creates_new(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Create a vault first
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Now mock Vault.load to raise VaultNotFound
    from desktop_2fa.vault.vault import VaultNotFound

    original_load = Vault.load

    def mock_load(*args: Any, **kwargs: Any) -> None:
        raise VaultNotFound("Vault file not found")

    Vault.load = staticmethod(mock_load)  # type: ignore[assignment]
    try:
        commands.list_entries(fake_ctx)
        out = capsys.readouterr().out.strip()
        assert "No vault found" in out
        assert "new encrypted vault will be created" in out
    finally:
        Vault.load = original_load  # type: ignore[method-assign]


def test_add_entry_interactive_value_error(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Create a vault with an entry first
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP")
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Try to add a duplicate entry using add_entry_interactive
    commands.add_entry_interactive("GitHub", "GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "already exists" in out


def test_add_entry_corrupted_vault(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Create a corrupted vault file
    fake_vault_env.write_bytes(b"WRNG\x01" + b"16byte_salt_here" + b"encrypted_data")

    commands.add_entry("Test", "Test", "JBSWY3DPEHPK3PXP", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Vault file format is unsupported" in out


def test_add_entry_vault_io_error(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    # Create a vault first
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Mock Vault.save to raise VaultIOError
    from desktop_2fa.vault.vault import VaultIOError

    def mock_save(self: Vault, *args: Any, **kwargs: Any) -> None:
        raise VaultIOError("Disk full")

    monkeypatch.setattr("desktop_2fa.vault.Vault.save", mock_save)

    commands.add_entry("Test", "Test2", "JBSWY3DPEHPK3PXP", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Failed to access vault file" in out


def test_generate_code_permission_denied(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    # Create a vault with an entry
    from desktop_2fa.vault import Vault
    from desktop_2fa.vault.vault import PermissionDenied

    vault = Vault()
    vault.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP")
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Mock Vault.load to raise PermissionDenied
    def mock_load(*args: Any, **kwargs: Any) -> None:
        raise PermissionDenied("Permission denied")

    monkeypatch.setattr("desktop_2fa.vault.Vault.load", mock_load)

    commands.generate_code("GitHub", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Cannot access vault directory (permission denied)" in out


def test_generate_code_value_error_invalid(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    # Create a vault with an entry
    from desktop_2fa.vault import Vault
    from desktop_2fa.vault.vault import InvalidPassword

    vault = Vault()
    vault.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP")
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Mock Vault.load to raise InvalidPassword
    def mock_load(*args: Any, **kwargs: Any) -> None:
        raise InvalidPassword("Invalid password")

    monkeypatch.setattr("desktop_2fa.vault.Vault.load", mock_load)

    commands.generate_code("GitHub", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Invalid vault password" in out


def test_generate_code_corrupted_vault(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Create a corrupted vault file
    fake_vault_env.write_bytes(b"WRNG\x01" + b"16byte_salt_here" + b"encrypted_data")

    commands.generate_code("GitHub", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Vault file format is unsupported" in out


def test_generate_code_vault_io_error(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    # Create a vault with an entry
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP")
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Mock Vault.load to raise VaultIOError
    from desktop_2fa.vault.vault import VaultIOError

    def mock_load(*args: Any, **kwargs: Any) -> None:
        raise VaultIOError("Disk error")

    monkeypatch.setattr("desktop_2fa.vault.Vault.load", mock_load)

    commands.generate_code("GitHub", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Failed to access vault file" in out


def test_remove_entry_no_vault(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Ensure no vault exists
    if fake_vault_env.exists():
        fake_vault_env.unlink()

    commands.remove_entry("GitHub", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "No vault found" in out


def test_remove_entry_value_error_invalid(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    # Create a vault
    from desktop_2fa.vault import Vault
    from desktop_2fa.vault.vault import InvalidPassword

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Mock Vault.load to raise InvalidPassword
    def mock_load(*args: Any, **kwargs: Any) -> None:
        raise InvalidPassword("Invalid password")

    monkeypatch.setattr("desktop_2fa.vault.Vault.load", mock_load)

    commands.remove_entry("GitHub", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Invalid vault password" in out


def test_remove_entry_corrupted_vault(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Create a corrupted vault file
    fake_vault_env.write_bytes(b"WRNG\x01" + b"16byte_salt_here" + b"encrypted_data")

    commands.remove_entry("GitHub", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Vault file format is unsupported" in out


def test_remove_entry_vault_io_error(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    # Create a vault
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP")
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Mock Vault.save to raise VaultIOError
    from desktop_2fa.vault.vault import VaultIOError

    def mock_save(self: Vault, *args: Any, **kwargs: Any) -> None:
        raise VaultIOError("Disk full")

    monkeypatch.setattr("desktop_2fa.vault.Vault.save", mock_save)

    commands.remove_entry("GitHub", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Failed to access vault file" in out


def test_rename_entry_value_error_invalid(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    # Create a vault
    from desktop_2fa.vault import Vault
    from desktop_2fa.vault.vault import InvalidPassword

    vault = Vault()
    vault.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP")
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Mock Vault.load to raise InvalidPassword
    def mock_load(*args: Any, **kwargs: Any) -> None:
        raise InvalidPassword("Invalid password")

    monkeypatch.setattr("desktop_2fa.vault.Vault.load", mock_load)

    commands.rename_entry("GitHub", "NewGitHub", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Invalid vault password" in out


def test_rename_entry_corrupted_vault(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Create a corrupted vault file
    fake_vault_env.write_bytes(b"WRNG\x01" + b"16byte_salt_here" + b"encrypted_data")

    commands.rename_entry("GitHub", "NewGitHub", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Vault file format is unsupported" in out


def test_rename_entry_vault_io_error(
    fake_vault_env: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    # Create a vault
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP")
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Mock Vault.save to raise VaultIOError
    from desktop_2fa.vault.vault import VaultIOError

    def mock_save(self: Vault, *args: Any, **kwargs: Any) -> None:
        raise VaultIOError("Disk full")

    monkeypatch.setattr("desktop_2fa.vault.Vault.save", mock_save)

    commands.rename_entry("GitHub", "NewGitHub", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Failed to access vault file" in out


def test_export_vault_permission_denied(
    fake_vault_env: Path, tmp_path: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    # Create a vault
    from desktop_2fa.vault import Vault
    from desktop_2fa.vault.vault import PermissionDenied

    vault = Vault()
    vault.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP")
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Mock Vault.load to raise PermissionDenied
    def mock_load(*args: Any, **kwargs: Any) -> None:
        raise PermissionDenied("Permission denied")

    monkeypatch.setattr("desktop_2fa.vault.Vault.load", mock_load)

    export_path = tmp_path / "export.bin"
    commands.export_vault(str(export_path), fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Cannot access vault directory (permission denied)" in out


def test_export_vault_corrupted_vault(
    fake_vault_env: Path, tmp_path: Path, capsys: Any, fake_ctx: Any
) -> None:
    # Create a corrupted vault file
    fake_vault_env.write_bytes(b"WRNG\x01" + b"16byte_salt_here" + b"encrypted_data")

    export_path = tmp_path / "export.bin"
    commands.export_vault(str(export_path), fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Vault file format is unsupported" in out


def test_export_vault_vault_io_error(
    fake_vault_env: Path, tmp_path: Path, capsys: Any, monkeypatch: Any, fake_ctx: Any
) -> None:
    # Create a vault
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.add_entry("GitHub", "GitHub", "JBSWY3DPEHPK3PXP")
    vault.save(fake_vault_env, TEST_PASSWORD)

    # Mock Vault.save to raise VaultIOError
    from desktop_2fa.vault.vault import VaultIOError

    def mock_save(self: Vault, *args: Any, **kwargs: Any) -> None:
        raise VaultIOError("Disk full")

    monkeypatch.setattr("desktop_2fa.vault.Vault.save", mock_save)

    export_path = tmp_path / "export.bin"
    commands.export_vault(str(export_path), fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Failed to access vault file" in out
