"""Argon2 key derivation utilities."""

from argon2.low_level import Type, hash_secret_raw


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a key from password and salt using Argon2id.

    Argon2id parameters (version 1.3, stable for 2025-era hardware):
    - time_cost: 4 iterations (balances security and performance)
    - memory_cost: 131072 KiB (128 MiB) (resistant to GPU attacks)
    - parallelism: 2 threads (suitable for most systems)
    - hash_len: 32 bytes (for AES-256)
    - salt_len: 16 bytes (recommended minimum)

    These parameters provide ~100ms derivation time on modern hardware
    while maintaining strong resistance to offline password guessing.

    Args:
        password: The password string.
        salt: The salt bytes (must be 16 bytes).

    Returns:
        The derived key bytes (32 bytes).
    """
    key = hash_secret_raw(
        secret=password.encode(),
        salt=salt,
        time_cost=4,
        memory_cost=128 * 1024,  # 128 MiB
        parallelism=2,
        hash_len=32,
        type=Type.ID,
    )
    return key
