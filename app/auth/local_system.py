"""Verify credentials against the local operating-system account store."""

from __future__ import annotations

import ctypes
import ctypes.util
import subprocess
import sys
from ctypes import (
    CFUNCTYPE,
    POINTER,
    Structure,
    byref,
    c_char,
    c_char_p,
    c_int,
    c_void_p,
    cast,
    create_string_buffer,
    pointer,
)


def verify_local_system_password(
    *,
    username: str,
    password: str,
    domain: str | None,
) -> bool:
    if not username.strip() or not password:
        return False

    if sys.platform == "win32":
        return _verify_windows(username.strip(), password, domain)

    if sys.platform == "darwin":
        return _verify_macos(username.strip(), password)

    if sys.platform.startswith("linux"):
        return _verify_unix_pam(username.strip(), password)

    return False


def _normalize_unix_username(username: str) -> str:
    return username.strip().split("\\")[-1].split("@")[0]


def _verify_macos(username: str, password: str) -> bool:
    """Verify a local macOS account password via Directory Services."""
    local_username = _normalize_unix_username(username)
    if not local_username:
        return False

    for datasource in ("/Local/Default", "."):
        if _macos_dscl_authonly(
            datasource=datasource,
            username=local_username,
            password=password,
        ):
            return True
    return False


def _macos_dscl_authonly(*, datasource: str, username: str, password: str) -> bool:
    try:
        result = subprocess.run(
            ["/usr/bin/dscl", datasource, "-authonly", username, password],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _verify_windows(username: str, password: str, domain: str | None) -> bool:
    try:
        advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    except OSError:
        return False

    token = ctypes.c_void_p()
    domain_name = domain.strip() if domain and domain.strip() else "."
    try:
        if not advapi32.LogonUserW(
            username,
            domain_name,
            password,
            2,  # LOGON32_LOGON_INTERACTIVE
            0,  # LOGON32_PROVIDER_DEFAULT
            byref(token),
        ):
            return False
        kernel32.CloseHandle(token)
        return True
    except Exception:
        return False


class _PamMessage(Structure):
    _fields_ = [("msg_style", c_int), ("msg", c_char_p)]


class _PamResponse(Structure):
    _fields_ = [("resp", c_char_p), ("resp_retcode", c_int)]


def _verify_unix_pam(username: str, password: str) -> bool:
    libpam_path = ctypes.util.find_library("pam")
    if not libpam_path:
        return False

    try:
        libpam = ctypes.CDLL(libpam_path)
    except OSError:
        return False

    for service in _pam_services():
        if _pam_authenticate(
            libpam=libpam,
            service=service,
            username=username,
            password=password,
        ):
            return True
    return False


def _pam_services() -> tuple[str, ...]:
    if sys.platform == "darwin":
        return ("login", "authorization", "system.login.console")
    return ("login",)


def _pam_authenticate(
    *,
    libpam: ctypes.CDLL,
    service: str,
    username: str,
    password: str,
) -> bool:
    pam_handle = c_void_p()
    password_bytes = password.encode("utf-8")
    password_buffer = create_string_buffer(password_bytes)
    stored_password = {"value": password_buffer}

    @CFUNCTYPE(
        c_int,
        c_int,
        POINTER(POINTER(_PamMessage)),
        POINTER(POINTER(_PamResponse)),
        c_void_p,
    )
    def _conversation(
        num_msg: int,
        msg: POINTER(POINTER(_PamMessage)),
        resp: POINTER(POINTER(_PamResponse)),
        _appdata_ptr: c_void_p,
    ) -> int:
        msg_list = cast(msg, POINTER(_PamMessage * num_msg)).contents
        responses = (_PamResponse * num_msg)()
        for index in range(num_msg):
            if msg_list[index].msg_style in (1, 2):  # PAM_PROMPT_ECHO_OFF/ON
                responses[index].resp = cast(stored_password["value"], c_char_p)
                responses[index].resp_retcode = 0
        resp.contents = cast(pointer(responses), POINTER(_PamResponse))
        return 0

    try:
        if libpam.pam_start(
            service.encode("utf-8"),
            username.encode("utf-8"),
            byref(_conversation),
            byref(pam_handle),
        ) != 0:
            return False

        try:
            return libpam.pam_authenticate(pam_handle, 0) == 0
        finally:
            libpam.pam_end(pam_handle, 0)
    except Exception:
        return False
