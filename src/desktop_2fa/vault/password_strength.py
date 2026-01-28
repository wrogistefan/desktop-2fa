# src/desktop_2fa/vault/password_strength.py

"""
Password strength evaluation module using zxcvbn.
"""

from typing import Any

from zxcvbn import zxcvbn


def evaluate_password_strength(password: str) -> dict[str, Any]:
    """
    Evaluate password strength using zxcvbn.

    Args:
        password: The password to evaluate.

    Returns:
        A dict with:
        - "score": int (0-4)
        - "feedback": dict with "warning" (str | None) and "suggestions" (list[str])
    """
    if not password:
        return {
            "score": 0,
            "feedback": {
                "warning": "Password is empty",
                "suggestions": ["Use a longer password with more variety"]
            }
        }
    
    result = zxcvbn(password)
    return {
        "score": result["score"],
        "feedback": {
            "warning": result["feedback"]["warning"],
            "suggestions": result["feedback"]["suggestions"],
        },
    }
