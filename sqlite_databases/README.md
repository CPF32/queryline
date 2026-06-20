# SQLite test databases

Local `.sqlite` files for trying the app without Docker or Postgres/MySQL.

**Do not confuse these with `text_to_sql_admin.db`** — that file in the project root is the app's own metadata store (registered data sources, imported schema, etc.). The files below are **query targets** you add as data sources in Admin.

## Build all databases

```bash
source .venv/bin/activate
python sqlite_databases/seed.py
```

Build one:

```bash
python sqlite_databases/seed.py --only retail
python sqlite_databases/seed.py --only hr
```

Generated files land in `sqlite_databases/databases/` (gitignored).

## Available databases

| File | Tables | Best for |
|------|--------|----------|
| `retail.sqlite` | 5 | Joins, revenue by region, order line analysis |
| `analytics.sqlite` | 4 | Simple counts/sums, basic FK relationships |
| `minimal.sqlite` | 1 | Smoke tests, single-table questions |
| `hr.sqlite` | 3 | Salary/headcount, different domain vocabulary |
| `inventory.sqlite` | 3 | NULL handling, low-stock filters, warehouse rollups |

### Sample questions

**retail**
- How many orders does each customer have?
- What is total revenue by region?
- Which products appear most often in order lines?

**analytics**
- What is total order amount by customer region?
- How many orders per customer?

**minimal**
- What is total revenue by region?
- Which day had the highest sales?

**hr**
- What is average salary by department?
- How many active employees do we have?

**inventory**
- Which SKUs are below reorder level?
- How much stock do we have per warehouse?

## Use in Admin UI

1. **Add data source** → connector **SQLite**
2. **Database file:** pick the absolute path, e.g.
   ```
   /Users/you/text-to-sql-analytics/sqlite_databases/databases/retail.sqlite
   ```
3. **Test connection** → **Import schema** → ask questions in Chat

## Register via API

With the backend running on port 5001:

```bash
python sqlite_databases/register_via_api.py --only retail
python sqlite_databases/register_via_api.py --only all
```

Connection presets live in `sqlite_databases/connections/`.

## Folder layout

```
sqlite_databases/
├── README.md
├── seed.py
├── register_via_api.py
├── schema/           # SQL source (committed)
│   ├── retail.sql
│   ├── analytics.sql
│   ├── minimal.sql
│   ├── hr.sql
│   └── inventory.sql
├── connections/      # Admin/API presets (committed)
└── databases/        # generated *.sqlite (gitignored)
```
