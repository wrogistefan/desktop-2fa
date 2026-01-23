import pyperclip


class ClipboardError(Exception):
    pass


def copy_to_clipboard(text: str) -> None:
    try:
        pyperclip.copy(text)
    except pyperclip.PyperclipException as exc:
        raise ClipboardError("Clipboard not available on this system.") from exc
