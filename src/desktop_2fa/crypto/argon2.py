from argon2.low_level import Type, hash_secret_raw


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a key from password and salt using Argon2.

    Args:
        password: The password string.
        salt: The salt bytes.

    Returns:
        The derived key bytes (32 bytes).
    """
    key = hash_secret_raw(
        secret=password.encode(),
        salt=salt,
        time_cost=3,
        memory_cost=64 * 1024,
        parallelism=2,
        hash_len=32,
        type=Type.ID,
    )
    return key
