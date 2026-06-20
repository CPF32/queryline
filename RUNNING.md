# Text-to-SQL Analytics — Integration Report

Verified on **2026-06-19** on macOS (darwin 25.2.0), Python 3.14.2, Node 18+.

---

## Stand up from a clean checkout

### 1. Backend

```bash
cd text-to-sql-analytics
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
```

### 2. Environment variables

| Variable | Required | Purpose | How to set |
|----------|----------|---------|------------|
| `DATABASE_URL` | no | SQLAlchemy URI for app metadata store | Default: `sqlite:///text_to_sql_admin.db` |
| `FERNET_KEY` | no* | Encrypts connection passwords at rest | Generate once and keep stable: `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'` |
| `ANTHROPIC_API_KEY` | yes for live chat | Claude SQL + chart generation | Export your Anthropic key |
| `ANTHROPIC_MODEL` | no | Claude model id | Default: `claude-sonnet-4-20250514` |
| `PORT` | no | Flask listen port | Default `5000` — on macOS, port 5000 is often taken by AirPlay Receiver; use `PORT=5001` if needed |
| `SECRET_KEY` | no | Flask session signing (unused today) | Optional for future auth |

\*If `FERNET_KEY` is omitted, a new key is generated on each process start and previously encrypted passwords become undecryptable. Set a stable key for any deployment that stores password-based connectors.

No `.env` file is shipped. Export variables in your shell or create a local `.env` and `source` it.

### 3. Metadata store init

There is **no Alembic** (or other migration tool). Tables are created automatically on first boot:

```python
# app/db.py → init_db() calls db.create_all()
```

Entities created: `data_sources`, `schema_tables`, `schema_columns`, `schema_relationships`, `glossary_terms`, `sql_examples`, `query_log_entries`.

**Gap:** schema changes require manual SQL or deleting the SQLite metadata file and re-importing. Alembic is not wired in.

### 4. Sample SQLite data source (optional but used in verification)

```bash
mkdir -p sample_data
python3 - <<'PY'
import sqlite3
from pathlib import Path
db = Path("sample_data/analytics.db")
conn = sqlite3.connect(db)
conn.executescript("""
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, region TEXT NOT NULL);
CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL, order_date TEXT NOT NULL, amount REAL NOT NULL, FOREIGN KEY (customer_id) REFERENCES customers(id));
CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL, product_id INTEGER NOT NULL, quantity INTEGER NOT NULL, unit_price REAL NOT NULL, FOREIGN KEY (order_id) REFERENCES orders(id), FOREIGN KEY (product_id) REFERENCES products(id));
INSERT INTO customers VALUES (1,'Acme Corp','North'),(2,'Beta LLC','South'),(3,'Gamma Inc','North');
INSERT INTO products VALUES (1,'Widget','Hardware'),(2,'Service Plan','Software');
INSERT INTO orders VALUES (1,1,'2026-01-15',150.0),(2,1,'2026-02-10',75.0),(3,2,'2026-01-20',200.0),(4,3,'2026-03-01',50.0);
INSERT INTO order_items VALUES (1,1,1,2,50.0),(2,2,2,1,75.0),(3,3,1,4,50.0),(4,4,2,1,50.0);
""")
conn.commit(); conn.close()
print(db.resolve())
PY
```

The integration run used `sample_data/analytics.db` with tables `customers`, `orders`, `order_items`, `products` and 3 FK relationships.

### 5. Run backend (integrated — API + built frontend)

```bash
source .venv/bin/activate
npm install
npm run build
export PORT=5001          # if 5000 is blocked
export FERNET_KEY='…'     # stable key recommended
export ANTHROPIC_API_KEY='…'  # required for live SQL generation
python run.py
```

Open **http://localhost:5001/** (chat) and **http://localhost:5001/admin** (metadata admin).

Health check:

```bash
curl http://localhost:5001/health
# {"status":"ok"}
```

### 6. Run frontend dev server (optional hot reload)

Terminal 1 — backend:

```bash
source .venv/bin/activate
export PORT=5001
python run.py
```

Terminal 2 — Vite (pick a port **not** used by macOS AirPlay — 5173/5174 are often hijacked):

```bash
npm run dev -- --port 3000
```

Vite proxies `/api` to Flask. Default target is `http://localhost:5000`; override when Flask uses another port:

```bash
VITE_API_PROXY=http://localhost:5001 npm run dev -- --port 3000 --host 127.0.0.1
```

Open **http://127.0.0.1:3000/**.

**CORS:** Not configured in Flask. Same-origin integrated mode (Flask serves `dist/`) needs no CORS. Cross-origin dev without the Vite proxy would require adding `flask-cors`.

---

## Verified end-to-end (commands run, results seen)

### Phase 1 — Backend boots

| Step | Command / action | Result |
|------|------------------|--------|
| venv + install | `pip install -r requirements.txt -e ".[dev]"` | Success |
| App factory | `python -c "from app import create_app; create_app()"` | `App created OK` |
| Server start | `PORT=5001 python run.py` | `Running on http://127.0.0.1:5001` |
| Health | `curl http://localhost:5001/health` | `{"status":"ok"}` |
| Connectors | `GET /api/v1/connectors` | 4 connectors: sqlite, postgresql, mysql, mssql |
| Test suite | `pytest tests/ -q` | **53 passed, 26 skipped** |

### Phase 2 — SQLite data source via API

Using `sample_data/analytics.db` and `POST /api/v1/data-sources`:

| Step | Result |
|------|--------|
| `POST /data-sources/test-connection` (sqlite) | `success: true`, ~0.3 ms latency |
| `POST /data-sources` | 201, `dialect_name: "sqlite"` |
| `POST …/schema/import` (merge, 4 tables) | `tables_imported: 4`, `columns_imported: 15`, `relationships_imported: 3` |
| `PUT …/schema/tables/{id}` | Description persisted |
| `PUT …/schema/columns/{id}` | Column description persisted |
| `POST …/glossary` | 201, term created |
| `POST …/examples` | 201, example created |
| `GET …/schema/tables` | 4 tables returned |

### Phase 3 — Generation loop (partial — no live API key in agent shell)

| Step | Result |
|------|--------|
| `POST /chat/execute` with hand-written SQL | 200, 3 rows, columns typed `string` + `integer` (after fix) |
| `POST /chat/chart-spec` (no `ANTHROPIC_API_KEY`) | 200, `chart_type: "table_only"` (after fix; was 500 before) |
| `POST /chat/execute` with `c.regoin` typo | 422, `validation_error`, suggests `region` |
| `POST /chat/generate-and-execute` (no API key) | 422, `generation_error` after 3 attempts — expected |
| Retry orchestration (mocked LLM) | `pytest tests/test_e2e_chat.py::test_negative_hallucinated_column_recovers_on_retry` **PASSED** |
| Full SQLite chat loop (mocked LLM) | `pytest tests/test_e2e_chat.py::test_e2e_sqlite_chat_loop` **PASSED** |
| Unsafe SQL rejection | `pytest tests/test_e2e_chat.py::test_negative_rejects_unsafe_sql` **PASSED** |

**Live Claude SQL generation:** Not verified in this session — `ANTHROPIC_API_KEY` was not available in the agent execution environment. Set the key locally and retry `POST /api/v1/chat/generate-and-execute`.

### Phase 4 — Frontend

| Step | Result |
|------|--------|
| `npm run build` | Success (`tsc -b && vite build`) |
| Integrated UI | `curl http://localhost:5001/` → 200, serves `dist/index.html` |
| API from same origin | `GET http://localhost:5001/api/v1/connectors` → 200 JSON |
| Vite dev proxy | **Verified** on `127.0.0.1:3000` with `VITE_API_PROXY=http://localhost:5001` — `GET /api/v1/connectors` returned 4 connectors. Ports 5173/5174 hit macOS AirPlay 403 on `/api/*`; use port 3000+ and `--host 127.0.0.1`. |

---

## Fixes applied during integration

### 1. Chart-spec 500 when `ANTHROPIC_API_KEY` unset (Agent 7)

**Symptom:** `POST /chat/chart-spec` returned HTTP 500 with unhandled `RuntimeError`.

**Fix:** `app/services/chart_spec_service.py` catches missing-key errors and returns `table_only` ChartSpec instead of crashing.

**Verified:** curl returned 200 with `chart_type: "table_only"`. Test added: `test_missing_api_key_falls_back_to_table_only`.

### 2. SQLite result column types `"unknown"` (Agent 3)

**Symptom:** Query results had `"type": "unknown"` for all columns, breaking chart heuristics.

**Fix:** `app/adapters/_common.py` → `refine_column_types()` infers logical types from row values; SQLite adapter applies it after fetch.

**Verified:** execute response now shows `"type": "string"` and `"type": "integer"`.

### 3. `requirements.txt` incomplete (Agent 1)

**Fix:** Added `psycopg2-binary`, `PyMySQL`, `pyodbc` so `pip install -r requirements.txt` alone installs adapter drivers (still run `pip install -e ".[dev]"` for editable package).

---

## Contract mismatches noted (not all fixed)

These are extensions or divergences from `CONTRACTS.md` that did not block the SQLite path:

| Area | Agent | Mismatch |
|------|-------|----------|
| API layout | 1 / 4 | Routes live under `app/api/admin/`; same handlers also registered at `/api/v1` **and** duplicate prefix `/api/admin`. Stub modules in `app/api/data_sources.py` etc. are doc-only. |
| SchemaColumn | 2 | DB/API expose `is_pii`, `is_excluded_from_prompt` — not in CONTRACTS §4.3. |
| GlossaryTerm | 2 | Extra optional `table_id`, `column_id` FKs. |
| All entities | 1 | `user_id`, `workspace_id` on every row (TenantMixin). |
| Schema API | 2 / 4 | Extra endpoints: `POST …/schema/introspect`, `POST …/import-schema`, `GET …/metadata-bundle`, `POST …/schema-tables`. Frontend uses introspect + import. |
| Chat API | 5 / 6 | Extra `POST /chat/generate-and-execute`; generate-sql response includes `chart_hint`, `attempt_number` beyond CONTRACTS §5.8. |
| Data sources | 4 | Extra `POST …/test` alias; `GET …/connection-form-schema` per connector and per data source. |
| Migrations | 1 | `db.create_all()` only — no Alembic revision chain. |
| CORS | 1 | Not implemented; fine for integrated deploy, required for cross-origin SPA without proxy. |

---

## Remaining punch list

| # | Issue | Agent | Why it matters |
|---|-------|-------|----------------|
| 1 | **Live LLM path unverified here** | 5 / 7 | Without `ANTHROPIC_API_KEY` in the runtime environment, `generate-sql` / `generate-and-execute` could not be exercised against real Claude. Mocked e2e tests pass. |
| 2 | **SQL Server path unverified** | 3 | `TEST_MSSQL_*` env vars unset; all MSSQL adapter/e2e tests skipped. SQLite success does not prove ODBC/tsql path. |
| 3 | **PostgreSQL / MySQL unverified live** | 3 | Same as MSSQL — contract tests skip without `TEST_POSTGRES_*` / MySQL env. |
| 4 | **No Alembic migrations** | 1 | Schema evolution requires manual intervention or wiping metadata DB. |
| 5 | **Chart-spec defaults to `table_only` without LLM** | 7 | Multi-row aggregated results (e.g. orders per customer) skip stat_card fallback and, without API key, never reach a bar chart. With API key, LLM path is used — not verified live. |
| 6 | **macOS port conflicts** | — | AirPlay Receiver commonly binds 5000, 5173, 5174. Documented workaround: `PORT=5001`, choose free Vite port, align proxy target. |
| 7 | **Vite proxy default port 5000** | 8 | Proxy target defaults to `localhost:5000`; override with `VITE_API_PROXY=http://localhost:5001` when Flask uses another port (common on macOS). |
| 8 | **Duplicate `/api/admin` blueprint registration** | 4 | Same routes at `/api/v1/...` and `/api/admin/...` — harmless but confusing; frontend uses `/api/v1` only. |
| 9 | **ChartSpec validation** | 7 | Invalid LLM field references fall back to `table_only` in unit tests; out-of-range `series_field` with a bad LLM response is not covered at UI level. |
| 10 | **Encrypted password rotation** | 1 | Changing `FERNET_KEY` invalidates stored passwords with no re-entry flow documented in UI. |

---

## Quick smoke-test script

After starting the server with a sample DB:

```bash
export BASE=http://localhost:5001/api/v1
export DB=/absolute/path/to/sample_data/analytics.db

# Create source
DS=$(curl -s -X POST "$BASE/data-sources" -H 'Content-Type: application/json' \
  -d "{\"name\":\"Smoke Test\",\"connector_type\":\"sqlite\",\"connection_config\":{\"file_path\":\"$DB\"},\"is_active\":true}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])")

# Import schema
curl -s -X POST "$BASE/data-sources/$DS/schema/import" -H 'Content-Type: application/json' \
  -d '{"mode":"merge","include_tables":["customers","orders"]}' | python3 -m json.tool

# Execute SQL
curl -s -X POST "$BASE/chat/execute" -H 'Content-Type: application/json' \
  -d "{\"data_source_id\":\"$DS\",\"session_id\":\"$(python3 -c 'import uuid; print(uuid.uuid4())')\",\"sql\":\"SELECT COUNT(*) AS n FROM orders\",\"user_question\":\"count orders\"}" \
  | python3 -m json.tool
```

---

## SQL Server verification status

**Not verified.** No SQL Server instance or `TEST_MSSQL_*` credentials were available during integration. MSSQL adapter code exists (`app/adapters/mssql/`) and registers in the connector list, but the end-to-end path was not exercised on this machine.
