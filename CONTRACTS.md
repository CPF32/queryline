# Text-to-SQL Analytics — Architecture Contracts

This document is the **single source of truth** for cross-agent interfaces. All
implementations must conform to these contracts. Nothing above the adapter layer
may branch on a specific database engine; use `dialect_name` (sqlglot string)
returned by the active adapter.

---

## 1. Repository Layout

```
text-to-sql-analytics/
├── CONTRACTS.md
├── app/                          # Python / Flask backend
│   ├── __init__.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py               # DataSourceAdapter ABC + adapter result types
│   │   └── registry.py           # connector_type → adapter class registry
│   ├── models/
│   │   ├── __init__.py
│   │   ├── data_source.py
│   │   ├── schema.py
│   │   ├── glossary.py
│   │   ├── sql_example.py
│   │   ├── query_log.py
│   │   ├── chart_spec.py
│   │   └── query_result.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── data_sources.py
│   │   ├── schema.py
│   │   ├── glossary.py
│   │   ├── examples.py
│   │   ├── chat.py
│   │   └── query_log.py
│   └── services/
│       ├── __init__.py
│       ├── adapter_factory.py
│       ├── schema_service.py
│       ├── sql_generation_service.py
│       ├── query_execution_service.py
│       └── chart_spec_service.py
└── src/                          # React frontend
    ├── admin/
    │   ├── DataSourcesPage.tsx
    │   ├── SchemaMetadataPage.tsx
    │   ├── GlossaryPage.tsx
    │   └── ExamplesPage.tsx
    ├── chat/
    │   ├── ChatPage.tsx
    │   ├── ChatMessageList.tsx
    │   └── QueryResultPanel.tsx
    └── components/
        ├── ChartRenderer.tsx
        ├── DataTable.tsx
        ├── ConnectionForm.tsx
        └── StatCard.tsx
```

---

## 2. Identifier Conventions

| Field            | Type   | Format / Notes                                      |
|------------------|--------|-----------------------------------------------------|
| `id` (all entities) | `str` | UUID v4 string (`xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`) |
| `data_source_id` | `str`  | FK to `DataSource.id`; scopes schema, glossary, examples, query log |
| `connector_type` | `str` | Opaque adapter registry key (e.g. `"postgresql"`, `"mssql"`). Used **only** by `adapter_factory` to instantiate an adapter. Must not appear in SQL-generation prompts; use `dialect_name` instead. |
| `dialect_name`   | `str`  | sqlglot dialect string from `DataSourceAdapter.get_dialect_name()` |

Timestamps are ISO-8601 UTC strings (`2026-06-19T14:30:00Z`).

---

## 3. DataSourceAdapter (Abstract Interface)

**Module:** `app.adapters.base`

Engine-specific behavior lives exclusively in adapter implementations under
`app/adapters/<connector_type>/`. All other layers depend on this ABC.

### 3.1 Abstract Base Class

```python
from abc import ABC, abstractmethod

class DataSourceAdapter(ABC):
    """Engine-specific bridge for connection, introspection, and read-only execution."""

    @abstractmethod
    def test_connection(self) -> ConnectionTestResult: ...

    @abstractmethod
    def introspect_schema(self) -> SchemaSnapshot: ...

    @abstractmethod
    def execute_readonly_query(
        self,
        sql: str,
        max_rows: int,
        timeout_seconds: int,
    ) -> QueryResult: ...

    @abstractmethod
    def get_dialect_name(self) -> str:
        """Return a valid sqlglot dialect string (e.g. 'tsql', 'postgres', 'mysql', 'sqlite')."""

    @classmethod
    @abstractmethod
    def get_connection_form_schema(cls) -> dict:
        """JSON-Schema-like dict describing admin UI fields for this connector."""
```

### 3.2 Adapter Result Types

These are returned by adapter methods and are **not** persisted entities.

#### `ConnectionTestResult`

| Field       | Type            | Required | Description                          |
|-------------|-----------------|----------|--------------------------------------|
| `success`   | `bool`          | yes      | Whether the connection succeeded     |
| `message`   | `str`           | yes      | Human-readable outcome               |
| `latency_ms`| `float \| null` | no       | Round-trip latency if successful     |

#### `SchemaSnapshot` (adapter output — not the persisted metadata model)

| Field    | Type                      | Required | Description                                      |
|----------|---------------------------|----------|--------------------------------------------------|
| `tables` | `list[SchemaTableDraft]`  | yes      | Introspected tables (see draft shape below)      |

`SchemaTableDraft` (introspection-only; maps to persisted `SchemaTable` on import):

| Field           | Type                         | Required |
|-----------------|------------------------------|----------|
| `schema_name`   | `str \| null`                | no       |
| `table_name`    | `str`                        | yes      |
| `row_count_estimate` | `int \| null`           | no       |
| `columns`       | `list[SchemaColumnDraft]`    | yes      |
| `relationships` | `list[SchemaRelationshipDraft]` | yes  |

`SchemaColumnDraft`:

| Field              | Type              | Required |
|--------------------|-------------------|----------|
| `column_name`      | `str`             | yes      |
| `data_type`        | `str`             | yes      | Native engine type as string |
| `is_nullable`      | `bool`            | yes      |
| `is_primary_key`   | `bool`            | yes      |
| `ordinal_position` | `int`             | yes      |
| `sample_distinct_values` | `list[str] \| null` | no | Populated for low-cardinality columns only |

`SchemaRelationshipDraft`:

| Field                 | Type   | Required |
|-----------------------|--------|----------|
| `constraint_name`     | `str`  | yes      |
| `source_table`        | `str`  | yes      |
| `source_column`       | `str`  | yes      |
| `target_table`        | `str`  | yes      |
| `target_column`       | `str`  | yes      |
| `relationship_type`   | `str`  | yes      | `"foreign_key"` (extensible) |

#### `QueryResult`

| Field            | Type                    | Required | Description                         |
|------------------|-------------------------|----------|-------------------------------------|
| `columns`        | `list[QueryColumnMeta]` | yes      | Result column metadata              |
| `rows`           | `list[list[Any]]`       | yes      | Row-major values (JSON-serializable)|
| `row_count`      | `int`                   | yes      | Number of rows returned             |
| `truncated`      | `bool`                  | yes      | `true` if `max_rows` limit hit      |
| `execution_ms`   | `float`                 | yes      | Wall-clock execution time           |

`QueryColumnMeta`:

| Field       | Type   | Required |
|-------------|--------|----------|
| `name`      | `str`  | yes      |
| `type`      | `str`  | yes      | Logical/declared type string        |

### 3.3 Connection Form Schema Contract

`get_connection_form_schema()` returns a dict compatible with JSON Schema draft-07
subset used by the admin UI:

```json
{
  "type": "object",
  "title": "PostgreSQL Connection",
  "properties": {
    "host": { "type": "string", "title": "Host", "default": "localhost" },
    "port": { "type": "integer", "title": "Port", "default": 5432 },
    "database": { "type": "string", "title": "Database" },
    "username": { "type": "string", "title": "Username" },
    "password": { "type": "string", "title": "Password", "format": "password" },
    "ssl_mode": {
      "type": "string",
      "title": "SSL Mode",
      "enum": ["disable", "require", "verify-full"],
      "default": "require"
    }
  },
  "required": ["host", "database", "username", "password"]
}
```

Supported property extensions for the admin renderer:

| Extension    | Type     | Purpose                                      |
|--------------|----------|----------------------------------------------|
| `format`     | `string` | `"password"` hides input; `"file"` file picker |
| `enum`       | `array`  | Renders `<select>`                           |
| `default`    | any      | Pre-fill value                               |
| `description`| `string` | Help text                                    |

**Example — SQL Server:**

```json
{
  "type": "object",
  "title": "SQL Server Connection",
  "properties": {
    "host": { "type": "string", "title": "Host" },
    "port": { "type": "integer", "title": "Port", "default": 1433 },
    "database": { "type": "string", "title": "Database" },
    "auth_mode": {
      "type": "string",
      "title": "Authentication",
      "enum": ["sql", "windows"],
      "default": "sql"
    },
    "username": { "type": "string", "title": "Username" },
    "password": { "type": "string", "title": "Password", "format": "password" }
  },
  "required": ["host", "database", "auth_mode"]
}
```

**Example — SQLite:**

```json
{
  "type": "object",
  "title": "SQLite Connection",
  "properties": {
    "file_path": { "type": "string", "title": "Database File", "format": "file" }
  },
  "required": ["file_path"]
}
```

### 3.4 Adapter Registry

**Module:** `app.adapters.registry`

```python
ADAPTER_REGISTRY: dict[str, type[DataSourceAdapter]] = {}
# Populated by concrete adapter modules at import time.
# Key = connector_type stored on DataSource.connector_type
```

`app.services.adapter_factory.get_adapter(data_source: DataSource) -> DataSourceAdapter`
instantiates the correct adapter from `connector_type` + `connection_config` dict.

---

## 4. Pydantic Domain Models

**Module:** `app.models.*`

All models:
- Subclass `pydantic.BaseModel`
- Expose `to_dict() -> dict` (alias for `.model_dump(mode="json")`)
- Expose `@classmethod from_dict(cls, data: dict) -> Self`

### 4.1 `DataSource`

**Module:** `app.models.data_source`

| Field               | Type            | Required | Description                                |
|---------------------|-----------------|----------|--------------------------------------------|
| `id`                | `str`           | yes      | UUID                                       |
| `name`              | `str`           | yes      | Display name (unique per deployment)       |
| `connector_type`    | `str`           | yes      | Adapter registry key                       |
| `connection_config` | `dict[str, Any]`| yes      | Opaque config matching form schema         |
| `is_active`         | `bool`          | yes      | Inactive sources hidden from chat picker   |
| `dialect_name`      | `str`           | yes      | Cached from adapter; refreshed on save/test |
| `created_at`        | `str`           | yes      | ISO-8601 UTC                               |
| `updated_at`        | `str`           | yes      | ISO-8601 UTC                               |

> `connection_config` secrets (passwords) are stored encrypted at rest by the
> persistence layer; API responses **mask** password fields as `"********"`.

### 4.2 `SchemaTable`

**Module:** `app.models.schema`

| Field                | Type            | Required |
|----------------------|-----------------|----------|
| `id`                 | `str`           | yes      |
| `data_source_id`     | `str`           | yes      |
| `schema_name`        | `str \| null`   | no       |
| `table_name`         | `str`           | yes      |
| `display_name`       | `str \| null`   | no       | Admin-friendly override |
| `description`        | `str \| null`   | no       |
| `is_included_in_prompt`| `bool`        | yes      | Whether LLM sees this table |
| `row_count_estimate` | `int \| null`   | no       |
| `created_at`         | `str`           | yes      |
| `updated_at`         | `str`           | yes      |

### 4.3 `SchemaColumn`

| Field                    | Type              | Required |
|--------------------------|-------------------|----------|
| `id`                     | `str`             | yes      |
| `table_id`               | `str`             | yes      |
| `column_name`            | `str`             | yes      |
| `display_name`           | `str \| null`     | no       |
| `description`            | `str \| null`     | no       |
| `data_type`              | `str`             | yes      |
| `is_nullable`            | `bool`            | yes      |
| `is_primary_key`         | `bool`            | yes      |
| `ordinal_position`       | `int`             | yes      |
| `sample_distinct_values` | `list[str] \| null` | no    |
| `created_at`             | `str`             | yes      |
| `updated_at`             | `str`             | yes      |

### 4.4 `SchemaRelationship`

| Field               | Type   | Required |
|---------------------|--------|----------|
| `id`                | `str`  | yes      |
| `data_source_id`    | `str`  | yes      |
| `constraint_name`   | `str`  | yes      |
| `source_table_id`   | `str`  | yes      |
| `source_column_id`  | `str`  | yes      |
| `target_table_id`   | `str`  | yes      |
| `target_column_id`  | `str`  | yes      |
| `relationship_type` | `str`  | yes      |
| `created_at`        | `str`  | yes      |
| `updated_at`        | `str`  | yes      |

### 4.5 `GlossaryTerm`

**Module:** `app.models.glossary`

| Field            | Type   | Required | Description                              |
|------------------|--------|----------|------------------------------------------|
| `id`             | `str`  | yes      |                                          |
| `data_source_id` | `str`  | yes      |                                          |
| `term`           | `str`  | yes      | Business term (e.g. "Active Customer")   |
| `definition`     | `str`  | yes      | Plain-language definition for the LLM    |
| `sql_expression` | `str \| null` | no  | Optional SQL fragment defining the term  |
| `created_at`     | `str`  | yes      |                                          |
| `updated_at`     | `str`  | yes      |                                          |

### 4.6 `SqlExample`

**Module:** `app.models.sql_example`

| Field            | Type   | Required | Description                    |
|------------------|--------|----------|--------------------------------|
| `id`             | `str`  | yes      |                                |
| `data_source_id` | `str`  | yes      |                                |
| `question`       | `str`  | yes      | Natural-language question      |
| `sql`            | `str`  | yes      | Reference SQL answer           |
| `notes`          | `str \| null` | no  | Optional annotation for LLM |
| `created_at`     | `str`  | yes      |                                |
| `updated_at`     | `str`  | yes      |                                |

### 4.7 `QueryLogEntry`

**Module:** `app.models.query_log`

| Field              | Type            | Required |
|--------------------|-----------------|----------|
| `id`               | `str`           | yes      |
| `data_source_id`   | `str`           | yes      |
| `session_id`       | `str`           | yes      | Chat session UUID |
| `user_question`    | `str`           | yes      |
| `generated_sql`    | `str`           | yes      |
| `execution_status` | `str`           | yes      | `"success"` \| `"validation_error"` \| `"execution_error"` |
| `error_message`    | `str \| null`   | no       |
| `row_count`        | `int \| null`   | no       |
| `execution_ms`     | `float \| null` | no       |
| `chart_spec`       | `dict \| null`  | no       | Serialized `ChartSpec` if generated |
| `created_at`       | `str`           | yes      |

### 4.8 `ChartSpec`

**Module:** `app.models.chart_spec`

| Field                  | Type              | Required | Description |
|------------------------|-------------------|----------|-------------|
| `chart_type`           | `ChartType`       | yes      | See enum below |
| `x_field`              | `str \| null`     | no       | Column name for x-axis / category |
| `y_fields`             | `list[str]`       | yes      | One or more measure columns |
| `series_field`         | `str \| null`     | no       | Column for series/color grouping |
| `aggregation_applied`  | `bool`            | yes      | Whether SQL already aggregated |
| `title`                | `str`             | yes      | Chart title |

#### `ChartType` Enum

```python
class ChartType(str, Enum):
    BAR = "bar"
    LINE = "line"
    AREA = "area"
    SCATTER = "scatter"
    PIE = "pie"
    STAT_CARD = "stat_card"
    TABLE_ONLY = "table_only"
```

#### ChartSpec JSON Example

```json
{
  "chart_type": "bar",
  "x_field": "region",
  "y_fields": ["total_revenue"],
  "series_field": null,
  "aggregation_applied": true,
  "title": "Revenue by Region"
}
```

#### Rendering Rules (frontend contract)

| `chart_type`  | Required fields                          | Recharts mapping (implementer note) |
|---------------|------------------------------------------|-------------------------------------|
| `bar`         | `x_field`, `y_fields`                    | `<BarChart>`                        |
| `line`        | `x_field`, `y_fields`                    | `<LineChart>`                       |
| `area`        | `x_field`, `y_fields`                    | `<AreaChart>`                       |
| `scatter`     | `x_field`, `y_fields[0]`                 | `<ScatterChart>`                    |
| `pie`         | `x_field` (label), `y_fields[0]` (value)| `<PieChart>`                        |
| `stat_card`   | `y_fields[0]`                            | Custom `StatCard` component         |
| `table_only`  | none                                     | Skip chart; table only              |

When `series_field` is set, frontend renders one series per distinct value.

---

## 5. REST API Contract

**Base URL:** `/api/v1`

**Common conventions:**
- Request/response bodies: JSON (`Content-Type: application/json`)
- Success responses wrap payloads: `{ "data": <T> }` unless noted
- List responses: `{ "data": [<T>], "meta": { "total": int } }`
- Errors: `{ "error": { "code": str, "message": str, "details": object|null } }`
- HTTP status: `200` OK, `201` Created, `204` No Content, `400` Bad Request,
  `404` Not Found, `422` Validation Error, `500` Internal Error

---

### 5.1 Connector Types (discovery)

#### `GET /connectors`

List available adapter types and their connection form schemas.

**Response 200:**
```json
{
  "data": [
    {
      "connector_type": "postgresql",
      "display_name": "PostgreSQL",
      "dialect_name": "postgres",
      "connection_form_schema": { "...": "..." }
    }
  ]
}
```

---

### 5.2 Data Sources

#### `GET /data-sources`

**Response 200:** `{ "data": [DataSource], "meta": { "total": N } }`

Password fields in `connection_config` are masked.

#### `GET /data-sources/{data_source_id}`

**Response 200:** `{ "data": DataSource }`

#### `POST /data-sources`

**Request:**
```json
{
  "name": "Production Warehouse",
  "connector_type": "postgresql",
  "connection_config": {
    "host": "db.example.com",
    "port": 5432,
    "database": "analytics",
    "username": "reader",
    "password": "secret"
  },
  "is_active": true
}
```

**Response 201:** `{ "data": DataSource }`

Server resolves `dialect_name` via adapter on create.

#### `PUT /data-sources/{data_source_id}`

Same body as POST (partial update allowed — omitted fields unchanged).

**Response 200:** `{ "data": DataSource }`

#### `DELETE /data-sources/{data_source_id}`

**Response 204**

---

### 5.3 Test Connection

#### `POST /data-sources/test-connection`

Test without persisting (used by admin form before save).

**Request:**
```json
{
  "connector_type": "postgresql",
  "connection_config": { "...": "..." }
}
```

**Response 200:**
```json
{
  "data": {
    "success": true,
    "message": "Connected successfully.",
    "latency_ms": 42.5
  }
}
```

#### `POST /data-sources/{data_source_id}/test-connection`

Test a saved data source (uses stored config).

**Response 200:** Same shape as above.

---

### 5.4 Schema Import

#### `POST /data-sources/{data_source_id}/schema/import`

Introspect live database and merge into persisted schema metadata.

**Request:**
```json
{
  "mode": "merge",
  "include_tables": ["public.orders", "public.customers"],
  "exclude_tables": null
}
```

`mode`: `"merge"` (update existing, add new) | `"replace"` (delete all metadata for this data source first).

**Response 200:**
```json
{
  "data": {
    "tables_imported": 12,
    "columns_imported": 87,
    "relationships_imported": 5
  }
}
```

---

### 5.5 Schema Metadata CRUD

All paths prefixed with `/data-sources/{data_source_id}/schema`.

#### Tables

| Method | Path              | Description        |
|--------|-------------------|--------------------|
| GET    | `/tables`         | List SchemaTable   |
| GET    | `/tables/{id}`    | Get one            |
| PUT    | `/tables/{id}`    | Update display_name, description, is_included_in_prompt |
| DELETE | `/tables/{id}`    | Delete table + columns |

**PUT /tables/{id} request:**
```json
{
  "display_name": "Customer Orders",
  "description": "One row per order line item",
  "is_included_in_prompt": true
}
```

#### Columns

| Method | Path                        | Description     |
|--------|-----------------------------|-----------------|
| GET    | `/tables/{table_id}/columns`| List columns    |
| PUT    | `/columns/{id}`             | Update metadata |

**PUT /columns/{id} request:**
```json
{
  "display_name": "Order Total",
  "description": "USD amount including tax"
}
```

#### Relationships

| Method | Path              | Description           |
|--------|-------------------|-----------------------|
| GET    | `/relationships`  | List SchemaRelationship |
| DELETE | `/relationships/{id}` | Remove relationship |

---

### 5.6 Glossary CRUD

Base: `/data-sources/{data_source_id}/glossary`

| Method | Path       | Description |
|--------|------------|-------------|
| GET    | `/`        | List terms  |
| POST   | `/`        | Create      |
| GET    | `/{id}`    | Get one     |
| PUT    | `/{id}`    | Update      |
| DELETE | `/{id}`    | Delete      |

**POST/PUT body:**
```json
{
  "term": "Active Customer",
  "definition": "A customer with at least one order in the last 90 days.",
  "sql_expression": "EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id AND o.order_date >= CURRENT_DATE - INTERVAL '90 days')"
}
```

---

### 5.7 SQL Examples CRUD

Base: `/data-sources/{data_source_id}/examples`

Same CRUD pattern as glossary.

**POST body:**
```json
{
  "question": "How many orders were placed last month?",
  "sql": "SELECT COUNT(*) FROM orders WHERE order_date >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month') AND order_date < date_trunc('month', CURRENT_DATE)",
  "notes": "Uses order_date column on orders table"
}
```

---

### 5.8 Chat — Generate SQL

#### `POST /chat/generate-sql`

**Request:**
```json
{
  "data_source_id": "uuid",
  "session_id": "uuid",
  "question": "Show me total revenue by region for Q1 2026",
  "conversation_history": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
```

**Response 200:**
```json
{
  "data": {
    "sql": "SELECT region, SUM(revenue) AS total_revenue FROM ...",
    "explanation": "Aggregates revenue by region filtering to Q1 2026.",
    "tables_referenced": ["orders", "regions"],
    "confidence": "high"
  }
}
```

`confidence`: `"high"` | `"medium"` | `"low"` (LLM self-assessment via structured output).

Implementation uses Claude tool-use / structured output. Prompt context includes:
- `dialect_name` (not connector_type)
- Included schema tables/columns/descriptions
- Glossary terms
- Few-shot SqlExamples

---

### 5.9 Execute Query

#### `POST /chat/execute`

Validate (read-only, single statement) and execute SQL.

**Request:**
```json
{
  "data_source_id": "uuid",
  "session_id": "uuid",
  "sql": "SELECT ...",
  "max_rows": 1000,
  "timeout_seconds": 30,
  "user_question": "Show me total revenue by region for Q1 2026"
}
```

**Response 200:**
```json
{
  "data": {
    "query_result": {
      "columns": [{ "name": "region", "type": "string" }],
      "rows": [["North", 125000.0]],
      "row_count": 1,
      "truncated": false,
      "execution_ms": 18.2
    },
    "query_log_id": "uuid"
  }
}
```

Validation layer (above adapter) must reject:
- Non-SELECT statements
- Multiple statements
- DDL/DML keywords

Creates a `QueryLogEntry` on every attempt.

---

### 5.10 Chart Spec

#### `POST /chat/chart-spec`

**Request:**
```json
{
  "data_source_id": "uuid",
  "session_id": "uuid",
  "user_question": "Show me total revenue by region for Q1 2026",
  "sql": "SELECT region, SUM(revenue) AS total_revenue FROM ...",
  "query_result": {
    "columns": [{ "name": "region", "type": "string" }, { "name": "total_revenue", "type": "float" }],
    "rows": [["North", 125000.0], ["South", 98000.0]],
    "row_count": 2,
    "truncated": false,
    "execution_ms": 18.2
  }
}
```

**Response 200:**
```json
{
  "data": {
    "chart_spec": {
      "chart_type": "bar",
      "x_field": "region",
      "y_fields": ["total_revenue"],
      "series_field": null,
      "aggregation_applied": true,
      "title": "Total Revenue by Region — Q1 2026"
    }
  }
}
```

Updates the associated `QueryLogEntry.chart_spec` when `query_log_id` is provided:

**Optional request field:** `"query_log_id": "uuid"`

---

### 5.11 Query Log

#### `GET /data-sources/{data_source_id}/query-log`

**Query params:** `session_id` (optional), `limit` (default 50), `offset` (default 0)

**Response 200:**
```json
{
  "data": [QueryLogEntry],
  "meta": { "total": 120, "limit": 50, "offset": 0 }
}
```

#### `GET /query-log/{id}`

**Response 200:** `{ "data": QueryLogEntry }`

---

## 6. Service Layer Boundaries

| Service                      | Responsibility                                      | Must NOT                          |
|------------------------------|-----------------------------------------------------|-----------------------------------|
| `adapter_factory`            | Resolve adapter from `DataSource`                   | Contain SQL generation logic      |
| `schema_service`             | CRUD + import orchestration                         | Execute user queries              |
| `sql_generation_service`     | Claude call, prompt assembly, structured SQL output | Reference engine-specific SQL     |
| `query_execution_service`    | Validate SQL (sqlglot), call adapter execute        | Mutate database                   |
| `chart_spec_service`         | Claude call for ChartSpec structured output         | Render charts                     |

---

## 7. Cross-Cutting Rules

1. **Multi-tenancy of data sources:** Every chat request must include `data_source_id`. Schema, glossary, examples, and query log are always scoped to a data source.

2. **Dialect-only above adapters:** SQL validation, formatting, and LLM prompts use `dialect_name` from the active `DataSource` record.

3. **Read-only execution:** Adapters MUST enforce read-only at the connection/session level where the engine supports it, in addition to application-layer SELECT-only validation.

4. **Secrets:** Never return raw passwords in API responses. Never log connection secrets.

5. **Extensibility:** New engines add a new adapter class + registry entry + connection form schema. No changes to API shapes or frontend contracts.

---

## 8. Versioning

Contract version: **1.0.0**

Breaking changes require incrementing major version and updating this document before implementation.
