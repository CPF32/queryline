"""SQLAlchemy persistence for admin metadata."""

from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON, Boolean, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


class TenantMixin:
    """Optional tenancy columns for future multi-tenant support."""

    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    workspace_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)


class DataSourceRow(TenantMixin, db.Model):
    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    connector_type: Mapped[str] = mapped_column(String(64), nullable=False)
    connection_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    dialect_name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False)


class SchemaTableRow(TenantMixin, db.Model):
    __tablename__ = "schema_tables"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    data_source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    schema_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    object_type: Mapped[str] = mapped_column(String(32), nullable=False, default="table")
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_included_in_prompt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    row_count_estimate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    return_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False)


class SchemaColumnRow(TenantMixin, db.Model):
    __tablename__ = "schema_columns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    table_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_type: Mapped[str] = mapped_column(String(255), nullable=False)
    is_nullable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_primary_key: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ordinal_position: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_distinct_values: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_pii: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_excluded_from_prompt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False)


class SchemaRelationshipRow(TenantMixin, db.Model):
    __tablename__ = "schema_relationships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    data_source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    constraint_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_table_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_column_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_table_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_column_id: Mapped[str] = mapped_column(String(36), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False, default="foreign_key")
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False)


class GlossaryTermRow(TenantMixin, db.Model):
    __tablename__ = "glossary_terms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    data_source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    term: Mapped[str] = mapped_column(String(255), nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    sql_expression: Mapped[str | None] = mapped_column(Text, nullable=True)
    table_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    column_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False)


class SqlExampleRow(TenantMixin, db.Model):
    __tablename__ = "sql_examples"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    data_source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    sql: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False)


class QueryLogEntryRow(TenantMixin, db.Model):
    __tablename__ = "query_log_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    data_source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    user_question: Mapped[str] = mapped_column(Text, nullable=False)
    generated_sql: Mapped[str] = mapped_column(Text, nullable=False)
    execution_status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    chart_spec: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)


class UserRow(db.Model):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_developer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    theme: Mapped[str] = mapped_column(String(16), nullable=False, default="dark")
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)
    last_seen_at: Mapped[str] = mapped_column(String(32), nullable=False)


class DiagnosticLogRow(db.Model):
    __tablename__ = "diagnostic_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="error")
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)


class ConversationRow(db.Model):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    data_source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False)
    archived_at: Mapped[str | None] = mapped_column(String(32), nullable=True)


class ConversationMessageRow(db.Model):
    __tablename__ = "conversation_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)


class QueryFeedbackRow(db.Model):
    __tablename__ = "query_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    query_log_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rating: Mapped[str] = mapped_column(String(8), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)


def _ensure_optional_columns() -> None:
    """Add columns introduced after initial deployments (SQLite-safe)."""
    from sqlalchemy import inspect, text

    engine = db.engine
    inspector = inspect(engine)

    if "sql_examples" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("sql_examples")}
        if "source" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE sql_examples ADD COLUMN source VARCHAR(32) DEFAULT 'manual'")
                )

    if "query_log_entries" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("query_log_entries")}
        if "conversation_id" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE query_log_entries ADD COLUMN conversation_id VARCHAR(36)"
                    )
                )

    if "conversations" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("conversations")}
        if "archived_at" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE conversations ADD COLUMN archived_at VARCHAR(32)")
                )

    if "schema_tables" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("schema_tables")}
        with engine.begin() as connection:
            if "object_type" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE schema_tables ADD COLUMN object_type VARCHAR(32) "
                        "DEFAULT 'table'"
                    )
                )
            if "definition" not in columns:
                connection.execute(
                    text("ALTER TABLE schema_tables ADD COLUMN definition TEXT")
                )
            if "return_type" not in columns:
                connection.execute(
                    text("ALTER TABLE schema_tables ADD COLUMN return_type VARCHAR(255)")
                )

    if "users" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("users")}
        with engine.begin() as connection:
            if "theme" not in columns:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN theme VARCHAR(16) DEFAULT 'dark'")
                )
            if "is_developer" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN is_developer BOOLEAN "
                        "DEFAULT 0 NOT NULL"
                    )
                )


def _ensure_owner_developer_flags() -> None:
    from app.services import setup_service

    state = setup_service.ensure_bootstrapped()
    owner_username = state.get("owner_username")
    if not owner_username:
        return

    rows = UserRow.query.all()
    updated = False
    for row in rows:
        if not setup_service.is_owner_user(username=row.username, domain=row.domain):
            continue
        if not row.is_admin or not row.is_developer:
            row.is_admin = True
            row.is_developer = True
            updated = True
    if updated:
        db.session.commit()


def init_db(app) -> None:
    db.init_app(app)
    with app.app_context():
        db.create_all()
        _ensure_optional_columns()
        _ensure_owner_developer_flags()
