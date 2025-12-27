from desktop_2fa.crypto.argon2 import derive_key
from desktop_2fa.crypto.aesgcm import encrypt, decrypt

def test_encrypt_decrypt():
    key, _ = derive_key("password")
    data = b"hello"
    enc = encrypt(key, data)
    dec = decrypt(key, enc)
    assert dec == data
