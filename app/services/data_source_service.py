"""Data source persistence and connection lifecycle."""

from __future__ import annotations

import uuid
from typing import Any

from app.adapters.base import ConnectionTestResult
from app.adapters.secrets import get_secret_manager
from app.db import DataSourceRow, db
from app.errors import ConnectionFailedError, NotFoundError, ValidationAppError
from app.models.data_source import DataSource
from app.repositories.mappers import data_source_from_row
from app.services.adapter_factory import _adapter_class, get_adapter, get_adapter_for_config
from app.util.time import utc_now_iso


def _mask_data_source(data_source: DataSource) -> DataSource:
    password_fields = _adapter_class(data_source.connector_type).password_field_names()
    masked_config = get_secret_manager().mask_connection_config(
        data_source.connection_config,
        password_fields=password_fields,
    )
    return data_source.model_copy(update={"connection_config": masked_config})


def list_data_sources() -> list[DataSource]:
    rows = DataSourceRow.query.order_by(DataSourceRow.name).all()
    return [_mask_data_source(data_source_from_row(row)) for row in rows]


def get_data_source(data_source_id: str) -> DataSource:
    row = _get_row(data_source_id)
    return _mask_data_source(data_source_from_row(row))


def _get_row(data_source_id: str) -> DataSourceRow:
    row = db.session.get(DataSourceRow, data_source_id)
    if row is None:
        raise NotFoundError(f"Data source {data_source_id} not found.")
    return row


def _test_and_verify(connector_type: str, connection_config: dict[str, Any]) -> ConnectionTestResult:
    adapter = get_adapter_for_config(connector_type, connection_config)
    result = adapter.test_connection()
    if not result.success:
        raise ConnectionFailedError(result.message, details=result.to_dict())
    readonly = adapter.verify_readonly_grants()
    if not readonly.success:
        raise ConnectionFailedError(readonly.message, details=readonly.to_dict())
    return result


def create_data_source(
    *,
    name: str,
    connector_type: str,
    connection_config: dict[str, Any],
    is_active: bool = True,
) -> DataSource:
    _test_and_verify(connector_type, connection_config)
    adapter = get_adapter_for_config(connector_type, connection_config)
    dialect_name = adapter.get_dialect_name()
    password_fields = adapter.password_field_names()
    encrypted_config = get_secret_manager().encrypt_connection_config(
        connection_config,
        password_fields=password_fields,
    )
    now = utc_now_iso()
    row = DataSourceRow(
        id=str(uuid.uuid4()),
        name=name,
        connector_type=connector_type,
        connection_config=encrypted_config,
        is_active=is_active,
        dialect_name=dialect_name,
        created_at=now,
        updated_at=now,
    )
    db.session.add(row)
    db.session.commit()
    return _mask_data_source(data_source_from_row(row))


def update_data_source(
    data_source_id: str,
    *,
    name: str | None = None,
    connector_type: str | None = None,
    connection_config: dict[str, Any] | None = None,
    is_active: bool | None = None,
) -> DataSource:
    row = _get_row(data_source_id)
    effective_connector = connector_type or row.connector_type

    if connector_type is not None and connector_type != row.connector_type and connection_config is None:
        raise ValidationAppError(
            "connection_config is required when changing connector_type."
        )

    if connection_config is not None:
        password_fields = _adapter_class(row.connector_type).password_field_names()
        merged_config = get_secret_manager().merge_password_on_update(
            connection_config,
            row.connection_config,
            password_fields=password_fields,
        )
        decrypted = get_secret_manager().decrypt_connection_config(
            merged_config,
            password_fields=_adapter_class(effective_connector).password_field_names(),
        )
        _test_and_verify(effective_connector, decrypted)
        adapter = get_adapter_for_config(effective_connector, decrypted)
        row.dialect_name = adapter.get_dialect_name()
        row.connection_config = get_secret_manager().encrypt_connection_config(
            merged_config,
            password_fields=adapter.password_field_names(),
        )
        row.connector_type = effective_connector

    if name is not None:
        row.name = name
    if is_active is not None:
        row.is_active = is_active
    row.updated_at = utc_now_iso()
    db.session.commit()
    return _mask_data_source(data_source_from_row(row))


def delete_data_source(data_source_id: str) -> None:
    row = _get_row(data_source_id)
    db.session.delete(row)
    db.session.commit()


def test_connection_for_config(
    connector_type: str,
    connection_config: dict[str, Any],
) -> ConnectionTestResult:
    adapter = get_adapter_for_config(connector_type, connection_config)
    return adapter.test_connection()


def test_saved_connection(data_source_id: str) -> ConnectionTestResult:
    data_source = data_source_from_row(_get_row(data_source_id))
    adapter = get_adapter(data_source)
    return adapter.test_connection()
