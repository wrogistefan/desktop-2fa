import pyperclip  # type: ignore[import-untyped]


class ClipboardError(Exception):
    pass


def copy_to_clipboard(text: str) -> None:
    try:
        pyperclip.copy(text)
    except Exception as exc:
        raise ClipboardError("Clipboard not available on this system.") from exc
