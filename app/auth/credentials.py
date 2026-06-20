"""Username and password authentication (LDAP / Active Directory or dev fallback)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from app.auth.local_system import verify_local_system_password


@dataclass(frozen=True)
class CredentialIdentity:
    username: str
    domain: str | None
    display_name: str


def split_domain_username(value: str) -> tuple[str | None, str]:
    normalized = value.strip()
    if not normalized:
        return None, ""
    if "\\" in normalized:
        domain, username = normalized.split("\\", 1)
        return domain.strip() or None, username.strip()
    if "@" in normalized:
        username, domain = normalized.split("@", 1)
        return domain.strip() or None, username.strip()
    return None, normalized


def normalize_login_identity(
    username: str,
    domain: str | None,
) -> CredentialIdentity:
    parsed_domain, parsed_username = split_domain_username(username)
    resolved_username = parsed_username or username.strip()
    resolved_domain = parsed_domain or (domain.strip() if domain else None)
    if not resolved_username:
        raise ValueError("Username is required.")
    label = (
        f"{resolved_domain}\\{resolved_username}"
        if resolved_domain
        else resolved_username
    )
    return CredentialIdentity(
        username=resolved_username,
        domain=resolved_domain,
        display_name=label,
    )


def _auth_mode() -> str:
    return os.environ.get("AUTH_MODE", "system").strip().lower()


def uses_local_system_password() -> bool:
    """True when sign-in should validate against the computer login password."""
    if os.environ.get("AUTH_LDAP_SERVER", "").strip():
        return False
    if os.environ.get("AUTH_DEV_PASSWORD", "").strip():
        return False
    return _auth_mode() == "system"


def credential_login_enabled() -> bool:
    if os.environ.get("AUTH_LDAP_SERVER", "").strip():
        return True
    if os.environ.get("AUTH_DEV_PASSWORD", "").strip():
        return True
    if uses_local_system_password():
        return True
    return _auth_mode() == "disabled"


def verify_credentials(
    *,
    username: str,
    password: str,
    domain: str | None,
) -> bool:
    if not password:
        return False

    ldap_server = os.environ.get("AUTH_LDAP_SERVER", "").strip()
    if ldap_server:
        return _ldap_authenticate(
            username=username,
            password=password,
            domain=domain,
            server_url=ldap_server,
        )

    if uses_local_system_password():
        return verify_local_system_password(
            username=username,
            password=password,
            domain=domain,
        )

    auth_mode = _auth_mode()
    dev_password = os.environ.get("AUTH_DEV_PASSWORD", "").strip()
    if auth_mode == "disabled" or dev_password:
        expected = dev_password or "dev"
        return password == expected

    return False


def _ldap_authenticate(
    *,
    username: str,
    password: str,
    domain: str | None,
    server_url: str,
) -> bool:
    try:
        import ldap3
    except ImportError:
        return False

    bind_template = os.environ.get(
        "AUTH_LDAP_BIND_DN",
        "{domain}\\{username}",
    ).strip()
    bind_user = bind_template.format(
        username=username,
        domain=domain or "",
    ).strip()
    if not bind_user:
        return False

    use_ssl = os.environ.get("AUTH_LDAP_USE_SSL", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    try:
        server = ldap3.Server(server_url, use_ssl=use_ssl, connect_timeout=5)
        connection = ldap3.Connection(
            server,
            user=bind_user,
            password=password,
            auto_bind=False,
            receive_timeout=5,
        )
        if not connection.bind():
            return False
        connection.unbind()
        return True
    except Exception:
        return False
