#!/usr/bin/env python3
"""Register all demo data sources with a running Flask API."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
CONNECTIONS = ROOT / "connections"
DEFAULT_BASE = "http://127.0.0.1:5001/api/v1"


def _resolve(entry: dict) -> dict:
    payload = json.loads(json.dumps(entry))
    file_path = payload["connection_config"].get("file_path", "")
    if isinstance(file_path, str):
        payload["connection_config"]["file_path"] = file_path.replace(
            "{{REPO_ROOT}}", str(REPO_ROOT)
        )
    return {
        "name": payload["name"],
        "connector_type": payload["connector_type"],
        "connection_config": payload["connection_config"],
        "is_active": payload.get("is_active", True),
    }


def _request(base: str, method: str, path: str, body: dict | None = None) -> dict:
    url = f"{base.rstrip('/')}{path}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _register(base: str, filename: str) -> None:
    entry = _resolve(json.loads((CONNECTIONS / filename).read_text(encoding="utf-8")))
    print(f"\n== {entry['name']} ==")

    test = _request(
        base,
        "POST",
        "/data-sources/test-connection",
        {
            "connector_type": entry["connector_type"],
            "connection_config": entry["connection_config"],
        },
    )
    result = test["data"]
    print(f"  test-connection: {result['message']}")
    if not result["success"]:
        raise RuntimeError(result["message"])

    created = _request(base, "POST", "/data-sources", entry)
    ds_id = created["data"]["id"]
    print(f"  created data source: {ds_id}")

    imported = _request(
        base,
        "POST",
        f"/data-sources/{ds_id}/schema/import",
        {"mode": "merge"},
    )
    stats = imported["data"]
    print(
        "  schema import:"
        f" {stats['tables_imported']} tables,"
        f" {stats['columns_imported']} columns,"
        f" {stats['relationships_imported']} relationships"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Register demo data sources via the REST API.")
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument(
        "--only",
        choices=["sqlite", "postgresql", "mysql", "mssql", "all"],
        default="sqlite",
    )
    args = parser.parse_args()

    profiles = {
        "sqlite": "sqlite.retail.json",
        "postgresql": "postgresql.retail.json",
        "mysql": "mysql.retail.json",
        "mssql": "mssql.retail.json",
    }

    if args.only in {"sqlite", "all"}:
        sys.path.insert(0, str(REPO_ROOT))
        from test_data.seed import seed_sqlite

        path = seed_sqlite()
        print(f"Seeded SQLite database at {path}")

    files = list(profiles.values()) if args.only == "all" else [profiles[args.only]]

    try:
        for filename in files:
            _register(args.base_url, filename)
    except urllib.error.URLError as exc:
        print(f"\nAPI error: {exc}")
        print("Is the backend running? Try: source .venv/bin/activate && python run.py")
        return 1
    except Exception as exc:
        print(f"\nFailed: {exc}")
        return 1

    print("\nDone. Open Admin → pick a data source → Schema → Chat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
