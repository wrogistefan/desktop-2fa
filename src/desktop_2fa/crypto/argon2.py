import os

from argon2.low_level import Type, hash_secret_raw


def derive_key(password: str, salt: bytes) -> bytes:
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
