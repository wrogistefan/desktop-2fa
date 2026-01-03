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
    assert out == [
        "No vault found.",
        "A new encrypted vault will be created.",
        "Vault created.",
        "No entries found.",
    ]


def test_add_entry_and_list(fake_vault_env: Path, capsys: Any, fake_ctx: Any) -> None:
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)

    # po add_entry:
    out = capsys.readouterr().out.strip().splitlines()
    assert out == [
        "No vault found.",
        "A new encrypted vault will be created.",
        "Vault created.",
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


def test_generate_code(fake_vault_env: Path, capsys: Any, fake_ctx: Any) -> None:
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)
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
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)
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
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)
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
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)
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

    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)
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
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)
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
    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)
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

    commands.add_entry("Test", "JBSWY3DPEHPK3PXP", fake_ctx_wrong_password)
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
    """Test adding entry from otpauth URL."""
    otpauth_url = "otpauth://totp/GitHub:octocat?secret=JBSWY3DPEHPK3PXP&issuer=GitHub"
    commands.add_entry(otpauth_url, "", fake_ctx)

    out = capsys.readouterr().out.strip().splitlines()
    assert "Entry added: GitHub" in out


def test_add_entry_invalid_otpauth_url(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    """Test adding entry with invalid otpauth URL."""
    invalid_url = "otpauth://invalid"
    commands.add_entry(invalid_url, "", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Invalid otpauth URL:" in out


def test_add_entry_invalid_secret(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    """Test adding entry with invalid Base32 secret."""
    commands.add_entry("Test", "invalid_secret", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Invalid secret: not valid Base32." in out


def test_list_entries_existing_vault_no_entries(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    """Test listing entries when vault exists but has no entries."""
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    commands.list_entries(fake_ctx)

    out = capsys.readouterr().out.strip().splitlines()
    assert "No entries found." in out


def test_generate_code_existing_vault_no_entries(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    """Test generating code when vault exists but has no entries."""
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    with pytest.raises(ValueError, match="not found"):
        commands.generate_code("nonexistent", fake_ctx)


def test_remove_entry_existing_vault_no_entries(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    """Test removing entry when vault exists but has no entries."""
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    with pytest.raises(ValueError, match="not found"):
        commands.remove_entry("nonexistent", fake_ctx)


def test_rename_entry_existing_vault_no_entries(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    """Test renaming entry when vault exists but has no entries."""
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    with pytest.raises(ValueError, match="not found"):
        commands.rename_entry("old", "new", fake_ctx)


def test_export_vault_existing_vault_no_entries(
    fake_vault_env: Path, tmp_path: Path, capsys: Any, fake_ctx: Any
) -> None:
    """Test exporting vault when it exists but has no entries."""
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
    """Test importing from corrupted vault file."""
    corrupted = tmp_path / "corrupted.bin"
    corrupted.write_text("corrupted data")

    commands.import_vault(str(corrupted), True, fake_ctx)
    out = capsys.readouterr().out.strip()
    assert "Source vault file format is unsupported." in out


def test_import_vault_unsupported_format(
    fake_vault_env: Path, tmp_path: Path, capsys: Any, fake_ctx: Any
) -> None:
    """Test importing from unsupported format."""
    unsupported = tmp_path / "unsupported.bin"
    # Create a file that looks like a vault but has unsupported format
    unsupported.write_bytes(b"unsupported_format_data")

    commands.import_vault(str(unsupported), True, fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Source vault file format is unsupported." in out


def test_backup_vault_existing_vault_no_entries(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    """Test backing up vault when it exists but has no entries."""
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
    """Test initializing vault when it already exists without force."""
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
    """Test initializing vault when it already exists with force."""
    from desktop_2fa.vault import Vault

    vault = Vault()
    vault.save(fake_vault_env, TEST_PASSWORD)

    commands.init_vault(True, fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Vault created." in out


def test_init_vault_new(fake_vault_env: Path, capsys: Any, fake_ctx: Any) -> None:
    """Test initializing new vault."""
    commands.init_vault(False, fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Vault created." in out
    assert fake_vault_env.exists()


def test_remove_entry_unsupported_format(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    """Test removing entry from unsupported vault format."""
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
    """Test renaming entry in unsupported vault format."""
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
    """Test exporting from unsupported vault format."""
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
    """Test backing up unsupported vault format."""
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
    """Test adding entry to unsupported vault format."""
    # Create a file with wrong magic header
    fake_vault_env.write_bytes(
        b"WRNG" + b"\x01" + b"16byte_salt_here" + b"encrypted_data"
    )

    commands.add_entry("GitHub", "JBSWY3DPEHPK3PXP", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Vault file format is unsupported." in out


def test_list_entries_unsupported_format(
    fake_vault_env: Path, capsys: Any, fake_ctx: Any
) -> None:
    """Test listing entries from unsupported vault format."""
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
    """Test generating code from unsupported vault format."""
    # Create a file with wrong magic header
    fake_vault_env.write_bytes(
        b"WRNG" + b"\x01" + b"16byte_salt_here" + b"encrypted_data"
    )

    commands.generate_code("GitHub", fake_ctx)

    out = capsys.readouterr().out.strip()
    assert "Vault file format is unsupported." in out
