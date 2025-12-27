from desktop_2fa.crypto.aesgcm import decrypt, encrypt
from desktop_2fa.crypto.argon2 import derive_key


def test_encrypt_decrypt():
    key, _ = derive_key("password")
    data = b"hello"
    enc = encrypt(key, data)
    dec = decrypt(key, enc)
    assert dec == data
