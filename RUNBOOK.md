# Text-to-SQL Analytics — Local Runbook

## Prerequisites

- Python 3.11+
- Node.js 18+
- Optional: ODBC Driver 18 for SQL Server + `unixodbc` (MSSQL adapter)
- Optional: PostgreSQL or MySQL instances for multi-engine testing
- `ANTHROPIC_API_KEY` for live LLM calls (tests mock Claude and do not require a key)

## Quick start

```bash
# Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"

# Frontend
npm install
npm run build

# Run integrated app (API + React static build)
python run.py
```

Open http://localhost:5000 for chat; http://localhost:5000/admin for metadata admin.

### Development mode (hot reload frontend)

Terminal 1:

```bash
source .venv/bin/activate
python run.py
```

Terminal 2:

```bash
npm run dev
```

Vite proxies `/api` to Flask on port 5000.

## Environment variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `DATABASE_URL` | SQLAlchemy URI for admin metadata | `sqlite:///text_to_sql_admin.db` |
| `ANTHROPIC_API_KEY` | Claude API key for SQL/chart generation | unset (required in production chat) |
| `ANTHROPIC_MODEL` | Claude model id | `claude-sonnet-4-20250514` |
| `PORT` | Flask listen port | `5000` |
| `TEST_POSTGRES_*` | Postgres adapter/E2E tests | optional |
| `TEST_MSSQL_*` | MSSQL adapter/E2E tests | optional |

## Running tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

SQLite E2E tests always run. MSSQL and Postgres E2E tests skip unless `TEST_MSSQL_*` / `TEST_POSTGRES_*` are set (same variables as `tests/test_adapter_contract.py`).

## Adding a 5th database engine

Only the adapter layer and factory registration should change. No API, service, or frontend contract changes.

1. **Create adapter package** — `app/adapters/<connector_type>/`
   - `adapter.py`: subclass `BaseDataSourceAdapter` from `app/adapters/_common.py`
   - Implement: `get_dialect_name()`, `get_connection_form_schema()`, `_connect()`, `_ping()`, `_check_readonly_grants()`, `_introspect_tables()`, `_execute_query()`
   - Register with `@register_adapter("<connector_type>", MyAdapter)` from `app/adapters/registry.py`

2. **Register on import** — `app/adapters/<connector_type>/__init__.py` exports the adapter class.

3. **Ensure lazy registration picks it up** — add `from app.adapters import <connector_type>` in `app/adapters/__init__.py` inside `ensure_adapters_registered()`.

4. **Dialect map (display only)** — add connector → sqlglot dialect in `app/services/adapter_factory.py` `_dialect_for()` if the registry key differs from the sqlglot name.

5. **Optional dialect prompt rules** — add entries to `DIALECT_RULES` in `app/services/sql_generation_service.py` so the LLM uses correct limit/identifier syntax.

6. **Contract tests** — add a `TestMyEngineAdapterContract` class in `tests/test_adapter_contract.py` and seed data instructions in this runbook.

Files you should **not** need to touch: `app/api/*`, `app/services/query_execution_service.py`, `app/services/chart_spec_service.py`, `src/types/contracts.ts`, React components.

## Architecture sanity check

The end-to-end loop is:

1. Admin configures data source → adapter verifies read-only access
2. Schema import → adapter introspection → persisted metadata
3. `POST /api/v1/chat/generate-sql` → prompt uses `dialect_name` + metadata (never `connector_type`)
4. `POST /api/v1/chat/execute` → sqlglot SELECT validation → adapter `execute_readonly_query`
5. `POST /api/v1/chat/chart-spec` → chart JSON from result shape

## Known limitations

- **LLM required for production chat** — without `ANTHROPIC_API_KEY`, generate-sql and chart-spec calls fail at runtime (tests mock the client).
- **Read-only enforcement** — application layer rejects non-SELECT SQL; adapters additionally verify DB grants on data-source save. Engines without granular grants rely on read-only connection settings (see `docs/READONLY_SETUP.md`).
- **MSSQL on macOS** — requires Homebrew `unixodbc` and Microsoft ODBC Driver 18; import fails gracefully when ODBC is missing.
- **Schema import** — `replace` mode deletes all metadata for a data source before re-import; live DB data is never mutated.
- **Session-scoped query log filtering** — `session_id` filter is applied in the API layer after fetch (adequate for demo scale).
- **Chart rendering** — pie/scatter with many categories fall back to `table_only`; stat-card auto-detects single-row numeric results without calling Claude.
- **No authentication** — single-tenant demo; add auth at the reverse proxy or Flask middleware for production.
- **Encrypted secrets** — connection passwords are encrypted at rest; use a stable `SECRET_KEY` / Fernet key in production deployments.
