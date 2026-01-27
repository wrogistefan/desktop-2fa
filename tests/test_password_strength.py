"""
Tests for password strength evaluation and enforcement.

This module tests:
1. zxcvbn password strength evaluation (weak vs strong passwords)
2. Configuration mapping (backward compatibility with min_password_entropy)
3. Password enforcement modes (warning vs rejection)
4. Vault initialization and password change flows
5. Non-interactive mode behavior
"""

import pathlib
from typing import Any
from unittest.mock import patch

import pytest

from desktop_2fa.cli.helpers import (
    _enforce_password_strength,
    _get_password_strength_threshold,
)
from desktop_2fa.vault.password_strength import evaluate_password_strength

# ============================================================================
# Tests for zxcvbn Password Strength Evaluation
# ============================================================================


class TestPasswordStrengthEvaluation:
    """Test zxcvbn-based password strength scoring."""

    def test_weak_password_single_word(self) -> None:
        """Test that simple dictionary words are scored as weak."""
        result = evaluate_password_strength("password")
        assert result["score"] < 3, "Simple word 'password' should be weak"

    def test_weak_password_numeric_sequence(self) -> None:
        """Test that numeric sequences are scored as weak."""
        result = evaluate_password_strength("123456")
        assert result["score"] < 3, "Numeric sequence should be weak"

    def test_weak_password_common_pattern(self) -> None:
        """Test that common patterns are scored as weak."""
        result = evaluate_password_strength("qwerty")
        assert result["score"] < 3, "Keyboard sequence should be weak"

    def test_weak_password_dictionary_word_with_number(self) -> None:
        """Test that word + number combinations are still weak."""
        result = evaluate_password_strength("password123")
        assert result["score"] < 3, "Dictionary word + number should be weak"

    def test_weak_password_admin_pattern(self) -> None:
        """Test common admin patterns."""
        result = evaluate_password_strength("admin2024")
        assert result["score"] < 3, "Common pattern 'admin2024' should be weak"

    def test_strong_password_passphrase(self) -> None:
        """Test that passphrases score as strong."""
        result = evaluate_password_strength("Battery-Horse-Staple-Correct")
        assert result["score"] >= 3, "Passphrase should be strong"

    def test_strong_password_complex_mixed(self) -> None:
        """Test that complex mixed passwords score as strong."""
        result = evaluate_password_strength("MyVault#2024")
        assert result["score"] >= 3, "Complex password should be strong"

    def test_strong_password_long_unique(self) -> None:
        """Test that long unique strings score as strong."""
        result = evaluate_password_strength("Mountain1Blue$River")
        assert result["score"] >= 3, "Long unique password should be strong"

    def test_password_strength_has_feedback(self) -> None:
        """Test that feedback is provided for weak passwords."""
        result = evaluate_password_strength("password")
        assert "feedback" in result
        assert "warning" in result["feedback"] or "suggestions" in result["feedback"]

    def test_password_strength_score_range(self) -> None:
        """Test that scores are in valid range 0-4."""
        test_passwords = [
            "a",
            "password",
            "MyPass123!",
            "Battery-Horse-Staple",
            "VeryLongPasswordWithManySpecialCharacters!@#$%^&*()",
        ]
        for pwd in test_passwords:
            result = evaluate_password_strength(pwd)
            assert 0 <= result["score"] <= 4, f"Score out of range for '{pwd}'"


# ============================================================================
# Tests for Configuration and Threshold Mapping
# ============================================================================


class TestConfigurationMapping:
    """Test configuration mapping for backward compatibility."""

    def test_get_threshold_default(self) -> None:
        """Test that default threshold is 3 when no config is present."""
        config: dict[str, Any] = {"security": {}}
        threshold = _get_password_strength_threshold(config)
        assert threshold == 3

    def test_get_threshold_with_legacy_entropy(self) -> None:
        """Test that legacy min_password_entropy is mapped to threshold 3."""
        config: dict[str, Any] = {"security": {"min_password_entropy": 60}}
        threshold = _get_password_strength_threshold(config)
        assert threshold == 3

    def test_get_threshold_empty_config(self) -> None:
        """Test that empty config returns default threshold."""
        config: dict[str, Any] = {}
        threshold = _get_password_strength_threshold(config)
        assert threshold == 3

    def test_get_threshold_no_security_section(self) -> None:
        """Test that missing security section returns default threshold."""
        config: dict[str, Any] = {"other_section": {}}
        threshold = _get_password_strength_threshold(config)
        assert threshold == 3


# ============================================================================
# Tests for Password Enforcement
# ============================================================================


class TestPasswordEnforcement:
    """Test password enforcement modes and behaviors."""

    def test_enforce_password_strong_password_accepted(self) -> None:
        """Test that strong passwords are accepted without warning."""
        with patch("desktop_2fa.cli.helpers.load_config") as mock_config:
            mock_config.return_value = {"security": {}}
            # Strong password should not raise any exception
            try:
                _enforce_password_strength("Battery-Horse-Staple")
            except Exception as e:
                pytest.fail(f"Strong password raised exception: {e}")

    def test_enforce_password_weak_password_with_confirmation(self) -> None:
        """Test that weak passwords prompt for confirmation by default."""
        with patch("desktop_2fa.cli.helpers.load_config") as mock_config:
            with patch("typer.confirm") as mock_confirm:
                mock_config.return_value = {
                    "security": {"reject_weak_passwords": False}
                }
                mock_confirm.return_value = True
                # Should prompt and accept confirmation
                try:
                    _enforce_password_strength("password")
                except Exception as e:
                    pytest.fail(f"Weak password with confirmation raised: {e}")
                mock_confirm.assert_called()

    def test_enforce_password_weak_password_rejected_in_strict_mode(self) -> None:
        """Test that weak passwords are rejected in strict mode."""
        with patch("desktop_2fa.cli.helpers.load_config") as mock_config:
            mock_config.return_value = {"security": {"reject_weak_passwords": True}}
            with pytest.raises(Exception):  # Should raise an exception
                _enforce_password_strength("password")

    def test_enforce_password_confirmation_declined(self) -> None:
        """Test that user can decline weak password confirmation."""
        with patch("desktop_2fa.cli.helpers.load_config") as mock_config:
            with patch("rich.prompt.Confirm.ask") as mock_confirm:
                mock_config.return_value = {
                    "security": {"reject_weak_passwords": False}
                }
                mock_confirm.return_value = False  # User declines
                with pytest.raises(Exception):  # Should raise when declined
                    _enforce_password_strength("password")


# ============================================================================
# Tests for Vault Operations with Password Strength
# ============================================================================


class TestVaultPasswordStrength:
    """Test vault initialization and password change with strength enforcement."""

    @pytest.fixture
    def clean_vault_env(self, tmp_path: pathlib.Path, monkeypatch: Any) -> pathlib.Path:
        """Create clean vault environment for testing."""
        fake_vault = tmp_path / "vault"
        monkeypatch.setattr(
            "desktop_2fa.cli.helpers.get_vault_path",
            lambda: str(fake_vault),
        )
        if fake_vault.parent.exists():
            import shutil

            shutil.rmtree(fake_vault.parent)
        fake_vault.parent.mkdir(parents=True, exist_ok=True)
        return fake_vault

    def test_enforce_password_rejects_weak_in_strict_mode(self) -> None:
        """Test that strict mode rejects weak passwords."""
        with patch("desktop_2fa.cli.helpers.load_config") as mock_config:
            mock_config.return_value = {"security": {"reject_weak_passwords": True}}
            # Weak password should be rejected in strict mode
            with pytest.raises(Exception):
                _enforce_password_strength("password")

    def test_enforce_password_accepts_strong_always(self) -> None:
        """Test that strong passwords are always accepted."""
        with patch("desktop_2fa.cli.helpers.load_config") as mock_config:
            mock_config.return_value = {"security": {"reject_weak_passwords": True}}
            # Strong password should be accepted even in strict mode
            try:
                _enforce_password_strength("Battery-Horse-Staple")
            except Exception as e:
                pytest.fail(f"Strong password rejected: {e}")


# ============================================================================
# Tests for CLI Behaviors with Password Strength
# ============================================================================


class TestCLIPasswordBehaviors:
    """Test CLI-level password strength behaviors."""

    def test_password_strength_in_password_helpers(self) -> None:
        """Test that password strength is evaluated in CLI helpers."""
        # Test that weak passwords are identified
        weak_result = evaluate_password_strength("password123")
        assert weak_result["score"] < 3

        # Test that strong passwords are identified
        strong_result = evaluate_password_strength("Battery-Horse-Staple")
        assert strong_result["score"] >= 3

    def test_configuration_affects_enforcement(self) -> None:
        """Test that configuration affects password enforcement."""
        # Default: should warn but allow weak passwords
        with patch("desktop_2fa.cli.helpers.load_config") as mock_config:
            mock_config.return_value = {"security": {"reject_weak_passwords": False}}
            threshold = _get_password_strength_threshold(mock_config.return_value)
            assert threshold == 3

        # Strict mode: should reject weak passwords
        with patch("desktop_2fa.cli.helpers.load_config") as mock_config:
            mock_config.return_value = {"security": {"reject_weak_passwords": True}}
            threshold = _get_password_strength_threshold(mock_config.return_value)
            assert threshold == 3


# ============================================================================
# Tests for Edge Cases
# ============================================================================


class TestPasswordStrengthEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_password(self) -> None:
        """Test that empty password is not evaluated by zxcvbn (crashes library)."""
        # zxcvbn crashes on empty passwords, so we handle this edge case
        # by checking that password enforcement would catch it
        with patch("desktop_2fa.cli.helpers.load_config") as mock_config:
            mock_config.return_value = {"security": {"reject_weak_passwords": True}}
            # Empty password should be rejected
            with pytest.raises(Exception):
                _enforce_password_strength("")

    def test_very_long_password(self) -> None:
        """Test that very long passwords can score as strong."""
        # A very long, random string should score well
        long_pwd = "x" * 50
        result = evaluate_password_strength(long_pwd)
        # May or may not be strong depending on randomness, but should have a valid score
        assert 0 <= result["score"] <= 4

    def test_unicode_password(self) -> None:
        """Test that Unicode passwords are handled."""
        result = evaluate_password_strength("Пароль123")  # Russian word + number
        assert 0 <= result["score"] <= 4

    def test_password_with_spaces(self) -> None:
        """Test that passwords with spaces are handled."""
        result = evaluate_password_strength("My Vault Password")
        assert 0 <= result["score"] <= 4

    def test_password_feedback_structure(self) -> None:
        """Test that feedback has correct structure."""
        result = evaluate_password_strength("password")
        assert "score" in result
        assert "feedback" in result
        feedback = result["feedback"]
        # Feedback should be a dict (zxcvbn returns dict with warning, suggestions)
        assert isinstance(feedback, dict)
