"""Resolve the active user from OS credentials or reverse-proxy SSO headers."""

from __future__ import annotations

import getpass
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ResolvedIdentity:
    """Normalized identity extracted from the incoming request context."""

    username: str
    domain: str | None
    display_name: str
    auth_mode: str


def _split_domain_username(value: str) -> tuple[str | None, str]:
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


def _system_username() -> str | None:
    for key in ("USERNAME", "USER"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    try:
        return getpass.getuser()
    except Exception:
        return None


def _system_domain() -> str | None:
    for key in ("USERDOMAIN", "DOMAIN"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return None


def resolve_identity(
    *,
    auth_mode: str,
    remote_user_header: str | None,
    system_user_header: str | None,
    dev_user_header: str | None,
) -> ResolvedIdentity | None:
    """Return the authenticated identity for the request, if any."""
    mode = (auth_mode or "system").strip().lower()

    if mode == "disabled":
        if dev_user_header:
            domain, username = _split_domain_username(dev_user_header)
            if username:
                label = f"{domain}\\{username}" if domain else username
                return ResolvedIdentity(
                    username=username,
                    domain=domain,
                    display_name=label,
                    auth_mode=mode,
                )
        return None

    if mode == "trusted_proxy":
        if not remote_user_header:
            return None
        domain, username = _split_domain_username(remote_user_header)
        if not username:
            return None
        label = f"{domain}\\{username}" if domain else username
        return ResolvedIdentity(
            username=username,
            domain=domain,
            display_name=label,
            auth_mode=mode,
        )

    if mode == "system":
        if system_user_header:
            domain, username = _split_domain_username(system_user_header)
            if username:
                label = f"{domain}\\{username}" if domain else username
                return ResolvedIdentity(
                    username=username,
                    domain=domain,
                    display_name=label,
                    auth_mode=mode,
                )
        username = _system_username()
        if not username:
            return None
        domain = _system_domain()
        label = f"{domain}\\{username}" if domain else username
        return ResolvedIdentity(
            username=username,
            domain=domain,
            display_name=label,
            auth_mode=mode,
        )

    return None
