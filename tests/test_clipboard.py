import pyperclip
import pytest

from desktop_2fa.cli.clipboard import ClipboardError, copy_to_clipboard


def test_copy_to_clipboard_success() -> None:
    # Skip test if clipboard is not available
    try:
        pyperclip.copy("dummy")
    except pyperclip.PyperclipException:
        pytest.skip("Clipboard not available on this system")

    # Test successful copy
    try:
        copy_to_clipboard("test")
    except ClipboardError:
        assert False, "copy_to_clipboard raised ClipboardError unexpectedly"


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
