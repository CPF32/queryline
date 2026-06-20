#!/usr/bin/env python3
"""Test demo connections directly via adapters (no Flask required)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
CONNECTIONS = ROOT / "connections"


def _resolve_config(raw: dict) -> dict:
    config = json.loads(json.dumps(raw))
    file_path = config.get("connection_config", {}).get("file_path", "")
    if isinstance(file_path, str) and "{{REPO_ROOT}}" in file_path:
        config["connection_config"]["file_path"] = file_path.replace(
            "{{REPO_ROOT}}", str(REPO_ROOT)
        )
    return config


def _load(name: str) -> dict:
    path = CONNECTIONS / name
    if not path.is_file():
        raise FileNotFoundError(path)
    return _resolve_config(json.loads(path.read_text(encoding="utf-8")))


def _test(entry: dict) -> bool:
    from app.services.adapter_factory import DataSourceFactory

    connector = entry["connector_type"]
    config = entry["connection_config"]
    adapter = DataSourceFactory.get_adapter_for_config(connector, config)

    print(f"\n== {entry.get('name', connector)} ({connector}) ==")
    result = adapter.test_connection()
    print(f"  connect: {'OK' if result.success else 'FAIL'} — {result.message}")
    if not result.success:
        return False

    readonly = adapter.verify_readonly_grants()
    print(f"  readonly: {'OK' if readonly.success else 'FAIL'} — {readonly.message}")
    if not readonly.success:
        return False

    snapshot = adapter.introspect_schema()
    tables = [t.table_name for t in snapshot.tables]
    print(f"  tables ({len(tables)}): {', '.join(sorted(tables))}")

    query = adapter.execute_readonly_query(
        "SELECT COUNT(*) AS order_count FROM orders",
        max_rows=10,
        timeout_seconds=30,
    )
    count = query.rows[0][0] if query.rows else "?"
    print(f"  sample query: SELECT COUNT(*) FROM orders → {count}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Test retail demo database connections.")
    parser.add_argument(
        "--only",
        choices=["sqlite", "postgresql", "mysql", "mssql", "all"],
        default="sqlite",
        help="Which connection profile to test (default: sqlite).",
    )
    args = parser.parse_args()

    profiles = {
        "sqlite": "sqlite.retail.json",
        "postgresql": "postgresql.retail.json",
        "mysql": "mysql.retail.json",
        "mssql": "mssql.retail.json",
    }

    if args.only == "all":
        selected = list(profiles.items())
    else:
        selected = [(args.only, profiles[args.only])]

    if args.only in {"sqlite", "all"}:
        from test_data.seed import seed_sqlite

        seed_sqlite()

    ok = True
    for _key, filename in selected:
        try:
            entry = _load(filename)
            ok = _test(entry) and ok
        except Exception as exc:
            print(f"\n== {filename} ==\n  ERROR: {exc}")
            ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    sys.path.insert(0, str(REPO_ROOT))
    raise SystemExit(main())
