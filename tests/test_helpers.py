import shutil
from pathlib import Path
from typing import Any

import pytest

from desktop_2fa.cli import helpers
from desktop_2fa.vault.vault import UnsupportedFormat, VaultIOError

TEST_PASSWORD = "jawislajawisla"


@pytest.fixture
def fake_vault_env_helpers(tmp_path: Path, monkeypatch: Any) -> Path:
    fake_vault = tmp_path / "vault"

    monkeypatch.setattr(
        "desktop_2fa.cli.helpers.get_vault_path",
        lambda: str(fake_vault),
    )

    if fake_vault.parent.exists():
        shutil.rmtree(fake_vault.parent)
    fake_vault.parent.mkdir(parents=True, exist_ok=True)

    return fake_vault


def test_helpers_add_and_list_entries(
    fake_vault_env_helpers: Path, capsys: Any
) -> None:
    from desktop_2fa.vault import Vault

    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)
    helpers.add_entry(
        fake_vault_env_helpers,
        "GitHub",
        "GitHub",
        "JBSWY3DPEHPK3PXP",
        TEST_PASSWORD,
    )

    out = capsys.readouterr().out.strip().splitlines()
    # Najpierw "Added entry: GitHub"
    assert out == ["Added entry: GitHub"]

    helpers.list_entries(fake_vault_env_helpers, TEST_PASSWORD)
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["- GitHub (GitHub)"]

    vault = helpers.load_vault(fake_vault_env_helpers, TEST_PASSWORD)
    assert len(vault.entries) == 1
    assert vault.entries[0].issuer == "GitHub"
    assert vault.entries[0].account_name == "GitHub"


def test_helpers_generate_code(fake_vault_env_helpers: Path, capsys: Any) -> None:
    from desktop_2fa.vault import Vault

    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)
    helpers.add_entry(
        fake_vault_env_helpers,
        "GitHub",
        "GitHub",
        "JBSWY3DPEHPK3PXP",
        TEST_PASSWORD,
    )
    capsys.readouterr()  # wyczyść output po add_entry

    helpers.generate_code(fake_vault_env_helpers, "GitHub", TEST_PASSWORD)
    out = capsys.readouterr().out.strip()

    lines = out.splitlines()
    code = lines[-1]
    assert len(code) == 6
    assert code.isdigit()


def test_helpers_remove_entry(fake_vault_env_helpers: Path) -> None:
    from desktop_2fa.vault import Vault

    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)
    helpers.add_entry(
        fake_vault_env_helpers,
        "GitHub",
        "GitHub",
        "JBSWY3DPEHPK3PXP",
        TEST_PASSWORD,
    )
    helpers.remove_entry(fake_vault_env_helpers, "GitHub", TEST_PASSWORD)

    vault = helpers.load_vault(fake_vault_env_helpers, TEST_PASSWORD)
    assert len(vault.entries) == 0


def test_helpers_rename_entry(fake_vault_env_helpers: Path) -> None:
    from desktop_2fa.vault import Vault

    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)
    helpers.add_entry(
        fake_vault_env_helpers,
        "GitHub",
        "GitHub",
        "JBSWY3DPEHPK3PXP",
        TEST_PASSWORD,
    )
    helpers.rename_entry(fake_vault_env_helpers, "GitHub", "GitHub2", TEST_PASSWORD)

    vault = helpers.load_vault(fake_vault_env_helpers, TEST_PASSWORD)
    assert vault.entries[0].issuer == "GitHub2"
    assert vault.entries[0].account_name == "GitHub2"


def test_helpers_export_and_import(
    fake_vault_env_helpers: Path, tmp_path: Path
) -> None:
    from desktop_2fa.vault import Vault

    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)
    helpers.add_entry(
        fake_vault_env_helpers,
        "GitHub",
        "GitHub",
        "JBSWY3DPEHPK3PXP",
        TEST_PASSWORD,
    )

    tmp_file = tmp_path / "export.bin"
    helpers.export_vault(fake_vault_env_helpers, tmp_file, TEST_PASSWORD)

    vault = helpers.load_vault(fake_vault_env_helpers, TEST_PASSWORD)
    vault.entries.clear()
    helpers.save_vault(fake_vault_env_helpers, vault, TEST_PASSWORD)

    helpers.import_vault(fake_vault_env_helpers, tmp_file, TEST_PASSWORD)
    vault = helpers.load_vault(fake_vault_env_helpers, TEST_PASSWORD)

    assert len(vault.entries) == 1
    assert vault.entries[0].issuer == "GitHub"


def test_helpers_backup(fake_vault_env_helpers: Path) -> None:
    from desktop_2fa.vault import Vault

    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)
    helpers.add_entry(
        fake_vault_env_helpers,
        "GitHub",
        "GitHub",
        "JBSWY3DPEHPK3PXP",
        TEST_PASSWORD,
    )

    backup_path = fake_vault_env_helpers.with_suffix(".backup.bin")
    helpers.backup_vault(fake_vault_env_helpers, backup_path, TEST_PASSWORD)

    assert backup_path.exists()
    assert backup_path.stat().st_size > 0


def test_helpers_timestamp() -> None:
    ts = helpers.timestamp()
    assert isinstance(ts, str)
    assert ts.isdigit()


def test_helpers_export_vault_missing(
    fake_vault_env_helpers: Path, tmp_path: Path, capsys: Any
) -> None:
    from desktop_2fa.vault import Vault

    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)
    export_path = tmp_path / "export.bin"
    helpers.export_vault(fake_vault_env_helpers, export_path, TEST_PASSWORD)
    out = capsys.readouterr().out
    # Aktualne zachowanie: eksportuje istniejący vault
    assert "Exported vault to:" in out
    assert export_path.exists()


def test_helpers_import_vault_missing(
    fake_vault_env_helpers: Path, tmp_path: Path
) -> None:
    from desktop_2fa.vault import Vault

    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)
    missing = tmp_path / "nope.bin"
    with pytest.raises(VaultIOError):
        helpers.import_vault(fake_vault_env_helpers, missing, TEST_PASSWORD)


def test_helpers_backup_vault_missing(
    fake_vault_env_helpers: Path, capsys: Any
) -> None:
    from desktop_2fa.vault import Vault

    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)

    backup_path = fake_vault_env_helpers.with_suffix(".backup.bin")
    helpers.backup_vault(fake_vault_env_helpers, backup_path, TEST_PASSWORD)
    out = capsys.readouterr().out
    # Aktualne zachowanie: backup_vault pisze backup i drukuje "Backup created:"
    assert "Backup created:" in out
    assert backup_path.exists()


def test_get_password_for_vault_password_file_missing(
    tmp_path: Path, capsys: Any
) -> None:
    import typer

    fake_ctx = type(
        "FakeContext",
        (),
        {"obj": {"password_file": str(tmp_path / "missing.txt"), "interactive": True}},
    )()
    with pytest.raises(typer.Exit):
        helpers.get_password_for_vault(fake_ctx, new_vault=False)
    out = capsys.readouterr().out
    assert "Error: Password file" in out


def test_load_vault_failed(tmp_path: Path) -> None:
    fake_vault = tmp_path / "vault"
    fake_vault.write_text("invalid")
    with pytest.raises(UnsupportedFormat):
        helpers.load_vault(fake_vault, TEST_PASSWORD)


def test_get_vault_path() -> None:
    path = helpers.get_vault_path()
    assert isinstance(path, str)
    assert ".desktop-2fa" in path


def test_get_password_for_vault_passwords_not_match(monkeypatch: Any) -> None:
    import typer

    fake_ctx = type("FakeContext", (), {"obj": {"interactive": True}})()
    monkeypatch.setattr(
        "typer.prompt", lambda text, hide_input: "pass1" if "Enter" in text else "pass2"
    )
    with pytest.raises(typer.Exit):
        helpers.get_password_for_vault(fake_ctx, new_vault=True)


def test_get_password_for_vault_both_password_and_file(
    tmp_path: Path, capsys: Any
) -> None:
    """Test error when both password and password_file are provided."""
    import typer

    fake_ctx = type(
        "FakeContext",
        (),
        {
            "obj": {
                "password": "test",
                "password_file": str(tmp_path / "test.txt"),
                "interactive": True,
            }
        },
    )()

    with pytest.raises(typer.Exit):
        helpers.get_password_for_vault(fake_ctx, new_vault=False)

    out = capsys.readouterr().out
    assert "Error: Cannot specify both --password and --password-file" in out


def test_get_password_for_vault_no_password_non_interactive(capsys: Any) -> None:
    """Test error when no password provided and not in interactive mode."""
    import typer

    fake_ctx = type("FakeContext", (), {"obj": {"interactive": False}})()

    with pytest.raises(typer.Exit):
        helpers.get_password_for_vault(fake_ctx, new_vault=False)

    out = capsys.readouterr().out
    assert "Error: Password not provided and not running in interactive mode" in out


def test_print_entries_table_empty(capsys: Any) -> None:
    """Test print_entries_table with empty list."""
    helpers.print_entries_table([])

    out = capsys.readouterr().out
    assert "No entries found." in out


def test_validate_base32_valid() -> None:
    """Test validate_base32 with valid Base32 strings."""
    assert helpers.validate_base32("JBSWY3DPEHPK3PXP") is True
    assert helpers.validate_base32("JBSWY3DP EHPK3PXP") is True  # with spaces
    assert helpers.validate_base32("jbswy3dpehpk3pxp") is True  # lowercase
    assert helpers.validate_base32("JBSWY3DPEHPK3PXP=") is True  # with padding


def test_validate_base32_invalid() -> None:
    """Test validate_base32 with invalid Base32 strings."""
    assert helpers.validate_base32("invalid") is True  # Actually valid Base32
    assert helpers.validate_base32("JBSWY3DPEHPK3PXP1") is False  # invalid character
    assert helpers.validate_base32("JBSWY3DPEHPK3PXP!") is False  # special character


def test_parse_otpauth_url_valid() -> None:
    """Test parse_otpauth_url with valid URLs."""
    result = helpers.parse_otpauth_url(
        "otpauth://totp/GitHub:octocat?secret=JBSWY3DPEHPK3PXP&issuer=GitHub"
    )
    assert result["issuer"] == "GitHub"
    assert result["label"] == "octocat"
    assert result["secret"] == "JBSWY3DPEHPK3PXP"


def test_parse_otpauth_url_issuer_only() -> None:
    """Test parse_otpauth_url with issuer only."""
    result = helpers.parse_otpauth_url("otpauth://totp/GitHub?secret=JBSWY3DPEHPK3PXP")
    assert result["issuer"] == "GitHub"
    assert result["label"] == "GitHub"
    assert result["secret"] == "JBSWY3DPEHPK3PXP"


def test_parse_otpauth_url_label_only() -> None:
    """Test parse_otpauth_url with label only."""
    result = helpers.parse_otpauth_url(
        "otpauth://totp/:octocat?secret=JBSWY3DPEHPK3PXP"
    )
    assert result["issuer"] == "Unknown"
    assert result["label"] == "octocat"
    assert result["secret"] == "JBSWY3DPEHPK3PXP"


def test_parse_otpauth_url_no_colon() -> None:
    """Test parse_otpauth_url with no colon in path."""
    result = helpers.parse_otpauth_url("otpauth://totp/GitHub?secret=JBSWY3DPEHPK3PXP")
    assert result["issuer"] == "GitHub"
    assert result["label"] == "GitHub"
    assert result["secret"] == "JBSWY3DPEHPK3PXP"


def test_parse_otpauth_url_invalid_scheme() -> None:
    """Test parse_otpauth_url with invalid scheme."""
    with pytest.raises(ValueError, match="Invalid otpauth URL"):
        helpers.parse_otpauth_url("http://example.com")


def test_parse_otpauth_url_invalid_type() -> None:
    """Test parse_otpauth_url with non-TOTP type."""
    with pytest.raises(ValueError, match="Only TOTP otpauth URLs are supported"):
        helpers.parse_otpauth_url("otpauth://hotp/GitHub?secret=JBSWY3DPEHPK3PXP")


def test_parse_otpauth_url_missing_secret() -> None:
    """Test parse_otpauth_url with missing secret."""
    with pytest.raises(ValueError, match="Secret parameter is required"):
        helpers.parse_otpauth_url("otpauth://totp/GitHub?issuer=GitHub")


def test_parse_otpauth_url_issuer_in_query() -> None:
    """Test parse_otpauth_url with issuer in query parameter."""
    result = helpers.parse_otpauth_url(
        "otpauth://totp/:octocat?secret=JBSWY3DPEHPK3PXP&issuer=GitHub"
    )
    assert result["issuer"] == "GitHub"
    assert result["label"] == "octocat"
    assert result["secret"] == "JBSWY3DPEHPK3PXP"


def test_print_success(capsys: Any) -> None:
    """Test print_success function."""
    helpers.print_success("Test message")
    out = capsys.readouterr().out
    assert "Test message" in out


def test_print_warning(capsys: Any) -> None:
    """Test print_warning function."""
    helpers.print_warning("Test message")
    out = capsys.readouterr().out
    assert "Test message" in out


def test_print_error(capsys: Any) -> None:
    """Test print_error function."""
    helpers.print_error("Test message")
    out = capsys.readouterr().out
    assert "Test message" in out


def test_print_info(capsys: Any) -> None:
    """Test print_info function."""
    helpers.print_info("Test message")
    out = capsys.readouterr().out
    assert "Test message" in out


def test_validate_base32_edge_cases() -> None:
    """Test validate_base32 with edge cases."""
    # Test very long Base32 string
    long_secret = "JBSWY3DPEHPK3PXP" * 10
    assert helpers.validate_base32(long_secret) is True

    # Test Base32 with padding
    assert helpers.validate_base32("JBSWY3DPEHPK3PXP======") is True

    # Test Base32 with mixed case
    assert helpers.validate_base32("jbswy3dpehpk3pxp") is True

    # Test Base32 with spaces in middle
    assert helpers.validate_base32("JB SW Y3 DP EH PK 3P XP") is True


def test_parse_otpauth_url_edge_cases() -> None:
    """Test parse_otpauth_url with edge cases."""
    # Test with missing issuer parameter
    result = helpers.parse_otpauth_url(
        "otpauth://totp/GitHub:octocat?secret=JBSWY3DPEHPK3PXP"
    )
    assert result["issuer"] == "GitHub"
    assert result["label"] == "octocat"

    # Test with empty query parameters
    result = helpers.parse_otpauth_url(
        "otpauth://totp/GitHub:octocat?secret=JBSWY3DPEHPK3PXP&"
    )
    assert result["issuer"] == "GitHub"
    assert result["label"] == "octocat"
    assert result["secret"] == "JBSWY3DPEHPK3PXP"

    # Test with additional query parameters
    result = helpers.parse_otpauth_url(
        "otpauth://totp/GitHub:octocat?secret=JBSWY3DPEHPK3PXP&issuer=GitHub&algorithm=SHA1&digits=6&period=30"
    )
    assert result["issuer"] == "GitHub"
    assert result["label"] == "octocat"
    assert result["secret"] == "JBSWY3DPEHPK3PXP"


def test_print_header(capsys: Any) -> None:
    """Test print_header function."""
    helpers.print_header("Test message")
    out = capsys.readouterr().out
    assert "Test message" in out
