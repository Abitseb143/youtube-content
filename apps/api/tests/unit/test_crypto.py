import base64

import pytest

from faceless.crypto import InvalidCiphertext, decrypt, encrypt

KEY_B64 = base64.b64encode(b"\x00" * 32).decode()


def test_encrypt_decrypt_roundtrip():
    plaintext = "ya29.refresh-token-secret"
    ct = encrypt(plaintext, KEY_B64)
    assert ct != plaintext
    assert decrypt(ct, KEY_B64) == plaintext


def test_encrypt_produces_different_ciphertext_each_call():
    p = "same-plaintext"
    assert encrypt(p, KEY_B64) != encrypt(p, KEY_B64)


def test_decrypt_with_wrong_key_raises():
    other_key = base64.b64encode(b"\x01" * 32).decode()
    ct = encrypt("secret", KEY_B64)
    with pytest.raises(InvalidCiphertext):
        decrypt(ct, other_key)


def test_decrypt_tampered_ciphertext_raises():
    ct = encrypt("secret", KEY_B64)
    raw = base64.b64decode(ct)
    tampered = raw[:20] + bytes([raw[20] ^ 0xFF]) + raw[21:]
    tampered_b64 = base64.b64encode(tampered).decode()
    with pytest.raises(InvalidCiphertext):
        decrypt(tampered_b64, KEY_B64)


def test_invalid_key_length_raises():
    short = base64.b64encode(b"\x00" * 16).decode()
    with pytest.raises(ValueError):
        encrypt("x", short)
