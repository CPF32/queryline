#!/usr/bin/env python3
"""Build local SQLite test databases from sqlite_databases/schema/*.sql."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEMA_DIR = ROOT / "schema"
OUTPUT_DIR = ROOT / "databases"

DATABASES: dict[str, str] = {
    "retail": "Five-table retail demo with regions, orders, and line items.",
    "analytics": "Four-table simple analytics schema (integration smoke-test shape).",
    "minimal": "Single-table daily sales — quick connection and count checks.",
    "hr": "Departments, employees, and salaries — different business vocabulary.",
    "inventory": "Warehouses, SKUs, and stock levels — NULLs and low-stock scenarios.",
}


def seed_one(name: str) -> Path:
    schema_path = SCHEMA_DIR / f"{name}.sql"
    if not schema_path.is_file():
        raise FileNotFoundError(f"Missing schema: {schema_path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    db_path = OUTPUT_DIR / f"{name}.sqlite"
    if db_path.exists():
        db_path.unlink()

    sql = schema_path.read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()
    return db_path.resolve()


def seed_all(names: list[str] | None = None) -> list[Path]:
    selected = names or list(DATABASES)
    return [seed_one(name) for name in selected]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create SQLite test databases.")
    parser.add_argument(
        "--only",
        choices=[*DATABASES.keys(), "all"],
        default="all",
        help="Which database(s) to build (default: all)",
    )
    args = parser.parse_args()

    names = list(DATABASES) if args.only == "all" else [args.only]
    for path in seed_all(names):
        print(f"Created {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
