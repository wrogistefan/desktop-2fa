"""Tests for clipboard functionality."""

import unittest
from unittest.mock import patch

from desktop_2fa.cli.clipboard import copy_to_clipboard, ClipboardError


class TestClipboard(unittest.TestCase):
    """Test clipboard operations."""

    @patch('desktop_2fa.cli.clipboard.pyperclip.copy')
    def test_copy_to_clipboard_success(self, mock_copy):
        """Test successful clipboard copy."""
        mock_copy.return_value = None
        copy_to_clipboard("123456")
        mock_copy.assert_called_once_with("123456")

    @patch('desktop_2fa.cli.clipboard.pyperclip.copy')
    def test_copy_to_clipboard_failure(self, mock_copy):
        """Test clipboard copy failure raises ClipboardError."""
        mock_copy.side_effect = Exception("Clipboard error")
        with self.assertRaises(ClipboardError) as cm:
            copy_to_clipboard("123456")
        self.assertIn("Clipboard not available", str(cm.exception))
        mock_copy.assert_called_once_with("123456")