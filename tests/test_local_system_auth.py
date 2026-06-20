"""Tests for local operating-system password verification."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.auth.local_system import verify_local_system_password


def test_verify_local_system_password_rejects_empty_credentials():
    assert verify_local_system_password(username="", password="secret", domain=None) is False
    assert verify_local_system_password(username="jdoe", password="", domain=None) is False


def test_verify_local_system_password_uses_dscl_on_macos(monkeypatch):
    monkeypatch.setattr("app.auth.local_system.sys.platform", "darwin")
    macos = MagicMock(return_value=True)
    monkeypatch.setattr("app.auth.local_system._verify_macos", macos)

    assert (
        verify_local_system_password(
            username="jdoe",
            password="secret",
            domain=None,
        )
        is True
    )
    macos.assert_called_once_with("jdoe", "secret")


def test_verify_local_system_password_uses_pam_on_linux(monkeypatch):
    monkeypatch.setattr("app.auth.local_system.sys.platform", "linux")
    pam = MagicMock(return_value=True)
    monkeypatch.setattr("app.auth.local_system._verify_unix_pam", pam)

    assert (
        verify_local_system_password(
            username="jdoe",
            password="secret",
            domain=None,
        )
        is True
    )
    pam.assert_called_once_with("jdoe", "secret")


def test_macos_dscl_authonly_success(monkeypatch):
    class Result:
        returncode = 0

    monkeypatch.setattr(
        "app.auth.local_system.subprocess.run",
        lambda *args, **kwargs: Result(),
    )
    from app.auth.local_system import _macos_dscl_authonly

    assert _macos_dscl_authonly(
        datasource="/Local/Default",
        username="jdoe",
        password="secret",
    )


def test_macos_normalizes_domain_username(monkeypatch):
    macos = MagicMock(return_value=True)
    monkeypatch.setattr("app.auth.local_system.sys.platform", "darwin")
    monkeypatch.setattr("app.auth.local_system._verify_macos", macos)

    verify_local_system_password(
        username="CORP\\jdoe",
        password="secret",
        domain=None,
    )
    macos.assert_called_once_with("CORP\\jdoe", "secret")


def test_verify_local_system_password_uses_logon_user_on_windows(monkeypatch):
    monkeypatch.setattr("app.auth.local_system.sys.platform", "win32")
    windows = MagicMock(return_value=True)
    monkeypatch.setattr("app.auth.local_system._verify_windows", windows)

    assert (
        verify_local_system_password(
            username="jdoe",
            password="secret",
            domain="CORP",
        )
        is True
    )
    windows.assert_called_once_with("jdoe", "secret", "CORP")
