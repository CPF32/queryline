"""Encrypt and mask connection secrets at rest.

Passwords are encrypted with ``cryptography.fernet`` before persistence and
masked in API responses after the initial save.
"""

from __future__ import annotations

import os
from copy import deepcopy
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.adapters._common import PASSWORD_MASK

ENCRYPTED_PREFIX = "enc:"


class SecretManager:
    """Fernet-backed secret encryption for connection configs."""

    def __init__(self, key: bytes | str | None = None) -> None:
        if key is not None:
            raw_key = key
        elif os.environ.get("FERNET_KEY"):
            raw_key = os.environ["FERNET_KEY"]
        else:
            from app.paths import ensure_fernet_key

            raw_key = ensure_fernet_key()
        if isinstance(raw_key, str):
            raw_key = raw_key.encode("utf-8")
        self._fernet = Fernet(raw_key)

    def encrypt(self, plaintext: str) -> str:
        token = self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")
        return f"{ENCRYPTED_PREFIX}{token}"

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext.startswith(ENCRYPTED_PREFIX):
            return ciphertext
        token = ciphertext[len(ENCRYPTED_PREFIX) :].encode("utf-8")
        try:
            return self._fernet.decrypt(token).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Unable to decrypt stored secret.") from exc

    def encrypt_field(self, value: str | None) -> str | None:
        if value is None or value == "":
            return value
        if value.startswith(ENCRYPTED_PREFIX):
            return value
        return self.encrypt(value)

    def decrypt_field(self, value: str | None) -> str | None:
        if value is None or value == "":
            return value
        if value.startswith(ENCRYPTED_PREFIX):
            return self.decrypt(value)
        return value

    def encrypt_connection_config(
        self,
        config: dict[str, Any],
        password_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        fields = password_fields or ["password"]
        encrypted = deepcopy(config)
        for field in fields:
            if field in encrypted and encrypted[field] not in (None, "", PASSWORD_MASK):
                encrypted[field] = self.encrypt_field(str(encrypted[field]))
        return encrypted

    def decrypt_connection_config(
        self,
        config: dict[str, Any],
        password_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        fields = password_fields or ["password"]
        decrypted = deepcopy(config)
        for field in fields:
            if field in decrypted and decrypted[field] not in (None, "", PASSWORD_MASK):
                decrypted[field] = self.decrypt_field(str(decrypted[field]))
        return decrypted

    def mask_connection_config(
        self,
        config: dict[str, Any],
        password_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        fields = password_fields or ["password"]
        masked = deepcopy(config)
        for field in fields:
            if field in masked and masked[field] not in (None, ""):
                masked[field] = PASSWORD_MASK
        return masked

    def merge_password_on_update(
        self,
        incoming: dict[str, Any],
        stored: dict[str, Any],
        password_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Keep stored password when the client sends the mask placeholder."""
        fields = password_fields or ["password"]
        merged = deepcopy(incoming)
        for field in fields:
            if merged.get(field) in (None, "", PASSWORD_MASK) and field in stored:
                merged[field] = stored[field]
        return merged


_default_manager: SecretManager | None = None


def get_secret_manager() -> SecretManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = SecretManager()
    return _default_manager
