import pyperclip
import pytest

from desktop_2fa.cli.clipboard import ClipboardError, copy_to_clipboard


def test_copy_to_clipboard_success(monkeypatch) -> None:
    copied_text: dict[str, str] = {}

    def fake_copy(text: str) -> None:
        copied_text["value"] = text

    # Mock pyperclip.copy so the test does not depend on the real clipboard
    monkeypatch.setattr(pyperclip, "copy", fake_copy)

    copy_to_clipboard("test")

    assert copied_text["value"] == "test"


def test_copy_to_clipboard_failure() -> None:
    # Test that ClipboardError is raised when pyperclip fails
    import unittest.mock as mock

    with mock.patch(
        "pyperclip.copy", side_effect=pyperclip.PyperclipException("Mocked failure")
    ):
        with pytest.raises(
            ClipboardError, match="Clipboard not available on this system."
        ):
            copy_to_clipboard("test")
