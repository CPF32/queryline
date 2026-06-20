"""Build the bundled Python backend used by packaged desktop installers."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist"
BACKEND_DIST = ROOT / "backend-dist"
WORK_DIR = ROOT / "build" / "pyinstaller"
SPEC_PATH = ROOT / "desktop" / "text-to-sql-backend.spec"

HIDDEN_IMPORTS = [
    "app",
    "app.api.admin",
    "app.api.admin.data_sources",
    "app.api.admin.examples",
    "app.api.admin.glossary",
    "app.api.admin.llm_settings",
    "app.api.admin.query_log",
    "app.api.admin.schema",
    "app.api.chat",
    "app.clients.claude_client",
    "app.clients.gemini_client",
    "app.clients.llm_factory",
    "app.clients.ollama_client",
    "flask",
    "flask_sqlalchemy",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.postgresql",
    "sqlalchemy.dialects.mysql",
    "sqlalchemy.dialects.mssql",
    "psycopg2",
    "pymysql",
    "pyodbc",
    "cryptography",
    "dotenv",
    "sqlglot",
    "anthropic",
    "google.genai",
    "werkzeug.serving",
]


def _ensure_frontend_built() -> None:
    if not (DIST_DIR / "index.html").is_file():
        raise SystemExit("Frontend build missing. Run `npm run build` first.")


def _clean_output() -> None:
    if BACKEND_DIST.exists():
        shutil.rmtree(BACKEND_DIST)
    WORK_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    _ensure_frontend_built()
    _clean_output()

    try:
        import PyInstaller  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "PyInstaller is required. Install it with: pip install pyinstaller"
        ) from exc

    add_data = f"{DIST_DIR}{os.pathsep}dist"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(SPEC_PATH),
        "--noconfirm",
        "--clean",
        f"--distpath={BACKEND_DIST}",
        f"--workpath={WORK_DIR}",
        f"--add-data={add_data}",
    ]
    for hidden in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", hidden])

    print("Building backend bundle...")
    subprocess.run(cmd, cwd=ROOT, check=True)
    print(f"Backend bundle ready in {BACKEND_DIST}")


if __name__ == "__main__":
    main()
