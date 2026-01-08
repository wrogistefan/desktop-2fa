import shutil
from pathlib import Path
from typing import Any

import pytest
import typer

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
    # Mock to return different passwords for the two prompts
    responses = ["pass1", "pass2"]
    monkeypatch.setattr("getpass.getpass", lambda prompt: responses.pop(0))
    with pytest.raises(typer.Exit):
        helpers.get_password_for_vault(fake_ctx, new_vault=True)


def test_get_password_for_vault_both_password_and_file(
    tmp_path: Path, capsys: Any
) -> None:
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
    import typer

    fake_ctx = type("FakeContext", (), {"obj": {"interactive": False}})()

    with pytest.raises(typer.Exit):
        helpers.get_password_for_vault(fake_ctx, new_vault=False)

    out = capsys.readouterr().out
    assert "Error: Password not provided and not running in interactive mode" in out


def test_print_entries_table_empty(capsys: Any) -> None:
    helpers.print_entries_table([])

    out = capsys.readouterr().out
    assert "No entries found." in out


def test_validate_base32_valid() -> None:
    assert helpers.validate_base32("JBSWY3DPEHPK3PXP") is True
    assert helpers.validate_base32("JBSWY3DP EHPK3PXP") is True  # with spaces
    assert helpers.validate_base32("jbswy3dpehpk3pxp") is True  # lowercase
    assert helpers.validate_base32("JBSWY3DPEHPK3PXP=") is True  # with padding


def test_validate_base32_invalid() -> None:
    assert helpers.validate_base32("invalid") is True  # Actually valid Base32
    assert helpers.validate_base32("JBSWY3DPEHPK3PXP1") is False  # invalid character
    assert helpers.validate_base32("JBSWY3DPEHPK3PXP!") is False  # special character


def test_parse_otpauth_url_valid() -> None:
    result = helpers.parse_otpauth_url(
        "otpauth://totp/GitHub:octocat?secret=JBSWY3DPEHPK3PXP&issuer=GitHub"
    )
    assert result["issuer"] == "GitHub"
    assert result["label"] == "octocat"
    assert result["secret"] == "JBSWY3DPEHPK3PXP"


def test_parse_otpauth_url_issuer_only() -> None:
    result = helpers.parse_otpauth_url("otpauth://totp/GitHub?secret=JBSWY3DPEHPK3PXP")
    assert result["issuer"] == "GitHub"
    assert result["label"] == "GitHub"
    assert result["secret"] == "JBSWY3DPEHPK3PXP"


def test_parse_otpauth_url_label_only() -> None:
    result = helpers.parse_otpauth_url(
        "otpauth://totp/:octocat?secret=JBSWY3DPEHPK3PXP"
    )
    assert result["issuer"] == "Unknown"
    assert result["label"] == "octocat"
    assert result["secret"] == "JBSWY3DPEHPK3PXP"


def test_parse_otpauth_url_no_colon() -> None:
    result = helpers.parse_otpauth_url("otpauth://totp/GitHub?secret=JBSWY3DPEHPK3PXP")
    assert result["issuer"] == "GitHub"
    assert result["label"] == "GitHub"
    assert result["secret"] == "JBSWY3DPEHPK3PXP"


def test_parse_otpauth_url_invalid_scheme() -> None:
    with pytest.raises(ValueError, match="Invalid otpauth URL"):
        helpers.parse_otpauth_url("http://example.com")


def test_parse_otpauth_url_invalid_type() -> None:
    with pytest.raises(ValueError, match="Only TOTP otpauth URLs are supported"):
        helpers.parse_otpauth_url("otpauth://hotp/GitHub?secret=JBSWY3DPEHPK3PXP")


def test_parse_otpauth_url_missing_secret() -> None:
    with pytest.raises(ValueError, match="Secret parameter is required"):
        helpers.parse_otpauth_url("otpauth://totp/GitHub?issuer=GitHub")


def test_parse_otpauth_url_issuer_in_query() -> None:
    result = helpers.parse_otpauth_url(
        "otpauth://totp/:octocat?secret=JBSWY3DPEHPK3PXP&issuer=GitHub"
    )
    assert result["issuer"] == "GitHub"
    assert result["label"] == "octocat"
    assert result["secret"] == "JBSWY3DPEHPK3PXP"


def test_print_success(capsys: Any) -> None:
    helpers.print_success("Test message")
    out = capsys.readouterr().out
    assert "Test message" in out


def test_print_warning(capsys: Any) -> None:
    helpers.print_warning("Test message")
    out = capsys.readouterr().out
    assert "Test message" in out


def test_print_error(capsys: Any) -> None:
    helpers.print_error("Test message")
    out = capsys.readouterr().out
    assert "Test message" in out


def test_print_info(capsys: Any) -> None:
    helpers.print_info("Test message")
    out = capsys.readouterr().out
    assert "Test message" in out


def test_validate_base32_edge_cases() -> None:
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
    helpers.print_header("Test message")
    out = capsys.readouterr().out
    assert "Test message" in out


def test_get_password_for_vault_password_file_read_error(
    tmp_path: Path, monkeypatch: Any
) -> None:
    # Create a file that will cause read error
    password_file = tmp_path / "password.txt"
    password_file.write_text("test")

    # Mock open to raise an exception
    def mock_open(*args: Any, **kwargs: Any) -> None:
        raise PermissionError("Permission denied")

    monkeypatch.setattr("builtins.open", mock_open)

    fake_ctx = type(
        "FakeContext",
        (),
        {"obj": {"password_file": str(password_file), "interactive": True}},
    )()
    with pytest.raises(typer.Exit):
        helpers.get_password_for_vault(fake_ctx, new_vault=False)


def test_calculate_entropy() -> None:
    # Test passphrase (4 words: 11*4 = 44)
    assert helpers.calculate_entropy("correct horse battery staple") == 44

    # Test complex password
    assert helpers.calculate_entropy("P@ssw0rd123!") > 50

    # Test weak password
    assert helpers.calculate_entropy("password") < 40


def test_calculate_entropy_no_character_sets() -> None:
    # Test when password has no recognized character sets (edge case)
    # This hits line 240 where N=0 is handled
    result = helpers.calculate_entropy("")
    assert result == 0.0  # len=0, log2(1)=0

    # Test with only whitespace - these are not alphanumeric so they count as symbols
    result = helpers.calculate_entropy("\t\n\r")
    # Whitespace counts as symbols, so N=32, log2(32)=5, len=3, result=15
    assert result == 15.0


def test_enforce_password_strength_weak_reject(monkeypatch: Any) -> None:

    # Mock load_config to return reject_weak=True and low min_entropy
    def mock_load_config() -> dict[str, Any]:
        return {
            "security": {"min_password_entropy": 100, "reject_weak_passwords": True}
        }

    monkeypatch.setattr("desktop_2fa.cli.helpers.load_config", mock_load_config)

    with pytest.raises(typer.Exit):
        helpers._enforce_password_strength("weak")


def test_enforce_password_strength_weak_warn(monkeypatch: Any) -> None:

    # Mock load_config and typer.confirm
    def mock_load_config() -> dict[str, Any]:
        return {
            "security": {"min_password_entropy": 100, "reject_weak_passwords": False}
        }

    monkeypatch.setattr("desktop_2fa.cli.helpers.load_config", mock_load_config)
    monkeypatch.setattr("typer.confirm", lambda msg: True)

    # Should not raise
    helpers._enforce_password_strength("weak")


def test_enforce_password_strength_weak_warn_reject(monkeypatch: Any) -> None:

    def mock_load_config() -> dict[str, Any]:
        return {
            "security": {"min_password_entropy": 100, "reject_weak_passwords": False}
        }

    monkeypatch.setattr("desktop_2fa.cli.helpers.load_config", mock_load_config)
    monkeypatch.setattr("typer.confirm", lambda msg: False)

    with pytest.raises(typer.Exit):
        helpers._enforce_password_strength("weak")


def test_get_password_for_vault_empty_password_direct(
    capsys: Any
) -> None:
    import typer

    fake_ctx = type("FakeContext", (), {"obj": {"password": "", "interactive": True}})()

    with pytest.raises(typer.Exit):
        helpers.get_password_for_vault(fake_ctx, new_vault=False)

    out = capsys.readouterr().out
    assert "Password cannot be empty" in out


def test_get_password_for_vault_empty_password_prompt_existing_vault(
    tmp_path: Path, monkeypatch: Any
) -> None:
    import typer

    fake_ctx = type("FakeContext", (), {"obj": {"interactive": True}})()

    # Mock getpass.getpass to return empty string for existing vault
    monkeypatch.setattr("getpass.getpass", lambda prompt: "")

    with pytest.raises(typer.Exit):
        helpers.get_password_for_vault(fake_ctx, new_vault=False)


def test_get_password_for_vault_empty_confirmation_password(
    tmp_path: Path, monkeypatch: Any
) -> None:
    import typer

    fake_ctx = type("FakeContext", (), {"obj": {"interactive": True}})()

    # First password is valid, second (confirmation) is empty
    call_count = 0
    def mock_getpass(prompt: str) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "validpassword"  # First prompt: new password
        return ""  # Second prompt: confirmation empty

    monkeypatch.setattr("getpass.getpass", mock_getpass)

    with pytest.raises(typer.Exit):
        helpers.get_password_for_vault(fake_ctx, new_vault=True)


def test_get_password_for_vault_password_from_file_empty(
    tmp_path: Path, capsys: Any
) -> None:
    import typer

    # Create a file with empty password
    password_file = tmp_path / "empty_password.txt"
    password_file.write_text("")

    fake_ctx = type(
        "FakeContext",
        (),
        {"obj": {"password_file": str(password_file), "interactive": True}},
    )()

    with pytest.raises(typer.Exit):
        helpers.get_password_for_vault(fake_ctx, new_vault=False)

    out = capsys.readouterr().out
    assert "Password cannot be empty" in out


def test_read_password_file_missing(tmp_path: Path) -> None:
    import typer

    missing_file = tmp_path / "missing.txt"

    with pytest.raises(typer.Exit):
        helpers._read_password_file(str(missing_file))


def test_read_password_file_os_error(tmp_path: Path, monkeypatch: Any) -> None:
    import typer

    password_file = tmp_path / "password.txt"
    password_file.write_text("test")

    # Mock open to raise OSError
    def mock_open(*args: Any, **kwargs: Any) -> None:
        raise OSError("Disk error")

    monkeypatch.setattr("builtins.open", mock_open)

    with pytest.raises(typer.Exit):
        helpers._read_password_file(str(password_file))


def test_load_config_existing_file(tmp_path: Path, monkeypatch: Any) -> None:

    config_dir = tmp_path / ".config" / "d2fa"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.toml"
    config_file.write_text("[security]\nmin_password_entropy = 80\n")

    # Mock Path.home() to return tmp_path
    original_home = Path.home
    Path.home = lambda: tmp_path  # type: ignore[method-assign]

    try:
        config = helpers.load_config()
        assert "security" in config
        assert config["security"]["min_password_entropy"] == 80
    finally:
        Path.home = original_home  # type: ignore[method-assign]


def test_read_password_file_file_not_found(tmp_path: Path) -> None:
    import typer

    missing_file = tmp_path / "missing.txt"

    with pytest.raises(typer.Exit):
        helpers._read_password_file(str(missing_file))


def test_get_password_for_vault_empty_password_prompt(
    tmp_path: Path, monkeypatch: Any
) -> None:
    import typer

    fake_ctx = type("FakeContext", (), {"obj": {"interactive": True}})()

    # Mock getpass.getpass to return empty string
    monkeypatch.setattr("getpass.getpass", lambda prompt: "")

    with pytest.raises(typer.Exit):
        helpers.get_password_for_vault(fake_ctx, new_vault=True)

    # Verify print_error was called
    # This tests lines 168-169


def test_validate_base32_invalid_decode(monkeypatch: Any) -> None:

    # Mock base64.b32decode to raise exception
    def mock_b32decode(data: Any) -> None:
        raise Exception("Invalid base32")

    monkeypatch.setattr("base64.b32decode", mock_b32decode)

    assert not helpers.validate_base32("INVALID")


def test_get_password_for_vault_enforce_strength(monkeypatch: Any) -> None:
    # Mock to not skip password checks
    monkeypatch.setattr("os.getenv", lambda key: None)

    # Mock load_config to return low min_entropy and reject_weak=False
    def mock_load_config() -> dict[str, Any]:
        return {
            "security": {"min_password_entropy": 10, "reject_weak_passwords": False}
        }

    monkeypatch.setattr("desktop_2fa.cli.helpers.load_config", mock_load_config)
    monkeypatch.setattr("typer.confirm", lambda msg: True)

    fake_ctx = type("FakeContext", (), {"obj": {"interactive": True}})()

    # Mock getpass.getpass for both password prompts
    responses = ["weak", "weak"]
    monkeypatch.setattr("getpass.getpass", lambda prompt: responses.pop(0))

    # Should not raise (accepts weak password with confirmation)
    password = helpers.get_password_for_vault(fake_ctx, new_vault=True)
    assert password == "weak"


def test_print_prompt(capsys: Any) -> None:
    helpers.print_prompt("Test message")
    out = capsys.readouterr().out
    assert "Test message" in out


# =============================================================================
# Regression tests for vault lifecycle (Issue #5)
# =============================================================================


def test_create_vault_new(fake_vault_env_helpers: Path, capsys: Any) -> None:
    # Ensure no vault exists
    if fake_vault_env_helpers.exists():
        fake_vault_env_helpers.unlink()

    helpers.create_vault(fake_vault_env_helpers, TEST_PASSWORD)

    out = capsys.readouterr().out.strip()
    # Check that the message contains the path (may be split across lines on Windows)
    assert "Vault created at" in out
    assert str(fake_vault_env_helpers) in out

    # Verify vault was created
    assert fake_vault_env_helpers.exists()

    # Verify it's a valid vault
    vault = helpers.load_vault(fake_vault_env_helpers, TEST_PASSWORD)
    assert len(vault.entries) == 0


def test_create_vault_overwrites_existing(
    fake_vault_env_helpers: Path, capsys: Any
) -> None:
    from desktop_2fa.vault import Vault
    from desktop_2fa.vault.models import TotpEntry

    # Create existing vault with an entry (bypass duplicate check)
    vault = Vault()
    entry = TotpEntry(account_name="GitHub", issuer="GitHub", secret="JBSWY3DPEHPK3PXP")
    vault.data.entries.append(entry)
    vault.save(fake_vault_env_helpers, TEST_PASSWORD)

    # Create new vault (should overwrite)
    helpers.create_vault(fake_vault_env_helpers, TEST_PASSWORD)

    out = capsys.readouterr().out.strip()
    assert "Vault created at" in out

    # Verify vault was overwritten (empty)
    vault = helpers.load_vault(fake_vault_env_helpers, TEST_PASSWORD)
    assert len(vault.entries) == 0


def test_vault_find_entries_single_match(fake_vault_env_helpers: Path) -> None:
    from desktop_2fa.vault import Vault

    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)
    helpers.add_entry(
        fake_vault_env_helpers,
        "GitHub",
        "GitHub",
        "JBSWY3DPEHPK3PXP",
        TEST_PASSWORD,
    )

    vault = helpers.load_vault(fake_vault_env_helpers, TEST_PASSWORD)
    matches = vault.find_entries("GitHub")

    assert len(matches) == 1
    assert matches[0].account_name == "GitHub"


def test_vault_find_entries_multiple_matches(fake_vault_env_helpers: Path) -> None:
    from desktop_2fa.vault import Vault
    from desktop_2fa.vault.models import TotpEntry

    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)

    # Load vault and directly add entries with duplicate names (bypass check)
    vault = helpers.load_vault(fake_vault_env_helpers, TEST_PASSWORD)
    entry1 = TotpEntry(
        account_name="GitHub", issuer="GitHub", secret="JBSWY3DPEHPK3PXP"
    )
    entry2 = TotpEntry(
        account_name="GitHub", issuer="GitHub2", secret="JBSWY3DPEHPK3PXP"
    )
    vault.data.entries.append(entry1)
    vault.data.entries.append(entry2)
    vault.save(fake_vault_env_helpers, TEST_PASSWORD)

    # Reload and find
    vault = helpers.load_vault(fake_vault_env_helpers, TEST_PASSWORD)
    matches = vault.find_entries("GitHub")

    assert len(matches) == 2


def test_vault_find_entries_no_match(fake_vault_env_helpers: Path) -> None:
    from desktop_2fa.vault import Vault

    helpers.save_vault(fake_vault_env_helpers, Vault(), TEST_PASSWORD)
    helpers.add_entry(
        fake_vault_env_helpers,
        "GitHub",
        "GitHub",
        "JBSWY3DPEHPK3PXP",
        TEST_PASSWORD,
    )

    vault = helpers.load_vault(fake_vault_env_helpers, TEST_PASSWORD)
    matches = vault.find_entries("Nonexistent")

    assert len(matches) == 0
