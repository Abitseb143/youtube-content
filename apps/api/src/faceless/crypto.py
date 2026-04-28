"""AES-GCM encryption for sensitive at-rest values (e.g., OAuth refresh tokens).

The key is a base64-encoded 32-byte secret loaded from `ENCRYPTION_KEY`.
Each call uses a fresh random 12-byte nonce, prepended to the ciphertext.
Output format (base64): nonce(12) || ciphertext || tag(16).
"""

import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class InvalidCiphertext(Exception):
    """Raised when ciphertext is malformed, tampered, or decrypted with the wrong key."""


def _load_key(key_b64: str) -> bytes:
    raw = base64.b64decode(key_b64)
    if len(raw) != 32:
        raise ValueError(f"ENCRYPTION_KEY must decode to 32 bytes, got {len(raw)}")
    return raw


def encrypt(plaintext: str, key_b64: str) -> str:
    key = _load_key(key_b64)
    aes = AESGCM(key)
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)
    return base64.b64encode(nonce + ct).decode("ascii")


def decrypt(ciphertext_b64: str, key_b64: str) -> str:
    key = _load_key(key_b64)
    try:
        raw = base64.b64decode(ciphertext_b64)
    except (ValueError, base64.binascii.Error) as e:
        raise InvalidCiphertext("malformed base64") from e
    if len(raw) < 12 + 16:
        raise InvalidCiphertext("ciphertext too short")
    nonce, ct = raw[:12], raw[12:]
    aes = AESGCM(key)
    try:
        return aes.decrypt(nonce, ct, associated_data=None).decode("utf-8")
    except InvalidTag as e:
        raise InvalidCiphertext("authentication failed") from e
