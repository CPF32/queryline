"""Desktop backend entrypoint launched by the Electron shell."""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# PyInstaller only bundles modules reachable from this entrypoint. Adapter
# packages are registered at import time, so import them here for desktop builds.
import app.adapters.mssql  # noqa: E402, F401
import app.adapters.mysql  # noqa: E402, F401
import app.adapters.postgresql  # noqa: E402, F401
import app.adapters.sqlite  # noqa: E402, F401


def _configure_runtime() -> None:
    os.environ.setdefault("DESKTOP_RUNTIME", "1")


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> None:
    _configure_runtime()

    try:
        from dotenv import load_dotenv

        from app.paths import get_env_file_path

        load_dotenv(get_env_file_path(), override=True)
    except ImportError:
        pass

    from app.paths import ensure_fernet_key, get_app_data_dir

    get_app_data_dir()
    ensure_fernet_key()

    port = _find_free_port()
    os.environ["PORT"] = str(port)

    from app import create_app

    app = create_app()
    print(f"BACKEND_READY:{port}", flush=True)

    from werkzeug.serving import run_simple

    run_simple(
        "127.0.0.1",
        port,
        app,
        use_reloader=False,
        use_debugger=False,
        threaded=True,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - surfaced in desktop logs
        print(f"BACKEND_ERROR:{exc}", file=sys.stderr, flush=True)
        raise
