"""Tests for connection secret encryption and masking."""

from app.adapters._common import PASSWORD_MASK
from app.adapters.secrets import SecretManager


def test_encrypt_decrypt_roundtrip() -> None:
    manager = SecretManager()
    encrypted = manager.encrypt("super-secret")
    assert encrypted.startswith("enc:")
    assert manager.decrypt(encrypted) == "super-secret"


def test_mask_connection_config() -> None:
    manager = SecretManager()
    masked = manager.mask_connection_config(
        {"host": "localhost", "password": "secret"},
        password_fields=["password"],
    )
    assert masked["host"] == "localhost"
    assert masked["password"] == PASSWORD_MASK


def test_merge_password_on_update() -> None:
    manager = SecretManager()
    stored = {"password": manager.encrypt("stored-secret")}
    merged = manager.merge_password_on_update(
        {"host": "localhost", "password": PASSWORD_MASK},
        stored,
        password_fields=["password"],
    )
    assert merged["password"] == stored["password"]
