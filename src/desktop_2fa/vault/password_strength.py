# src/desktop_2fa/vault/password_strength.py

"""
Password strength evaluation module using zxcvbn.
"""

from zxcvbn import zxcvbn

def evaluate_password_strength(password: str) -> dict:
    """
    Evaluate password strength using zxcvbn.

    Args:
        password: The password to evaluate.

    Returns:
        A dict with:
        - "score": int (0-4)
        - "feedback": dict with "warning" (str | None) and "suggestions" (list[str])
    """
    result = zxcvbn(password)
    return {
        "score": result["score"],
        "feedback": {
            "warning": result["feedback"]["warning"],
            "suggestions": result["feedback"]["suggestions"]
        }
    }
