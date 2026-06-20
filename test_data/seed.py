#!/usr/bin/env python3
"""Create the SQLite retail demo database (delegates to sqlite_databases/)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlite_databases.seed import seed_one as _seed_one


def seed_sqlite() -> Path:
    return _seed_one("retail")


if __name__ == "__main__":
    path = seed_sqlite()
    print(f"Created {path}")
