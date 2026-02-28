"""Field-level encryption for sensitive data at rest.

Uses Fernet (AES-128-CBC + HMAC-SHA256) with a key derived from SECRET_KEY.
To rotate keys, set CONNECTOR_ENCRYPTION_KEY to a new Fernet key and
re-encrypt stored values.
"""

from __future__ import annotations

import base64
import os
from functools import lru_cache

import structlog

logger = structlog.get_logger()

_SENTINEL_PREFIX = "enc:"  # Prefix to identify encrypted values


@lru_cache(maxsize=1)
def _get_fernet():
    """Return a Fernet instance. Key derived from CONNECTOR_ENCRYPTION_KEY or SECRET_KEY."""
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from app.core.config import settings

    raw_key = os.environ.get("CONNECTOR_ENCRYPTION_KEY") or settings.SECRET_KEY
    # Derive a 32-byte key using PBKDF2 with a fixed salt
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"scr-connector-keys-v1",
        iterations=100_000,
    )
    derived = kdf.derive(raw_key.encode("utf-8"))
    fernet_key = base64.urlsafe_b64encode(derived)
    return Fernet(fernet_key)


def encrypt_field(plaintext: str | None) -> str | None:
    """Encrypt a string field. Returns None if input is None."""
    if plaintext is None:
        return None
    try:
        fernet = _get_fernet()
        token = fernet.encrypt(plaintext.encode("utf-8"))
        return _SENTINEL_PREFIX + token.decode("utf-8")
    except Exception as exc:
        logger.error("field_encryption_failed", error=str(exc))
        raise


def decrypt_field(ciphertext: str | None) -> str | None:
    """Decrypt a string field. Returns None if input is None.

    If the value does not have the sentinel prefix (e.g. legacy plain-text),
    returns it as-is so pre-existing data is still readable.
    """
    if ciphertext is None:
        return None
    if not ciphertext.startswith(_SENTINEL_PREFIX):
        # Legacy plain-text value — return as-is
        return ciphertext
    try:
        fernet = _get_fernet()
        token = ciphertext[len(_SENTINEL_PREFIX):].encode("utf-8")
        return fernet.decrypt(token).decode("utf-8")
    except Exception as exc:
        logger.error("field_decryption_failed", error=str(exc))
        raise
