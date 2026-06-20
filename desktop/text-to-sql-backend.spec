# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

block_cipher = None
spec_dir = Path(SPECPATH).resolve()
root = spec_dir.parent

hiddenimports = [
    "app",
    "app.api.admin",
    "app.api.admin.data_sources",
    "app.api.admin.examples",
    "app.api.admin.glossary",
    "app.api.admin.llm_settings",
    "app.api.admin.query_log",
    "app.api.admin.schema",
    "app.api.auth",
    "app.api.chat",
    "app.api.setup",
    "app.api.users",
    "app.clients.claude_client",
    "app.clients.gemini_client",
    "app.clients.llm_factory",
    "app.clients.ollama_client",
    "app.services.setup_service",
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

a = Analysis(
    [str(root / "desktop" / "server.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / "dist"), "dist")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="text-to-sql-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
