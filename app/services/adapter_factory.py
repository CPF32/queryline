"""Factory for resolving DataSourceAdapter instances from DataSource records.

Uses ADAPTER_REGISTRY keyed by connector_type. Must not contain SQL
generation or validation logic.

See CONTRACTS.md §3.4 and §6.
"""

from __future__ import annotations

from typing import Any

from app.adapters.base import DataSourceAdapter
from app.adapters.registry import ADAPTER_REGISTRY
from app.adapters.secrets import get_secret_manager
from app.errors import UnknownConnectorError
from app.models.data_source import DataSource


def _ensure_registered() -> None:
    from app.adapters import ensure_adapters_registered

    ensure_adapters_registered()


def _adapter_class(connector_type: str) -> type[DataSourceAdapter]:
    _ensure_registered()
    adapter_cls = ADAPTER_REGISTRY.get(connector_type)
    if adapter_cls is None:
        raise UnknownConnectorError(connector_type)
    return adapter_cls


def get_adapter_for_config(
    connector_type: str,
    connection_config: dict[str, Any],
    *,
    decrypt_secrets: bool = False,
) -> DataSourceAdapter:
    adapter_cls = _adapter_class(connector_type)
    config = dict(connection_config)
    if decrypt_secrets:
        config = get_secret_manager().decrypt_connection_config(
            config,
            password_fields=adapter_cls.password_field_names(),
        )
    return adapter_cls(config)


def get_adapter(data_source: DataSource) -> DataSourceAdapter:
    """Instantiate the adapter for the given data source."""
    return get_adapter_for_config(
        data_source.connector_type,
        data_source.connection_config,
        decrypt_secrets=True,
    )


class DataSourceFactory:
    """Instantiates engine adapters from persisted data source records."""

    get_adapter = staticmethod(get_adapter)
    get_adapter_for_config = staticmethod(get_adapter_for_config)
    create = staticmethod(get_adapter)

    @staticmethod
    def list_connectors() -> list[dict]:
        _ensure_registered()
        connectors: list[dict] = []
        for connector_type, adapter_cls in sorted(ADAPTER_REGISTRY.items()):
            schema = adapter_cls.get_connection_form_schema()
            connectors.append(
                {
                    "connector_type": connector_type,
                    "display_name": schema.get("title", connector_type),
                    "dialect_name": _probe_dialect_name(adapter_cls),
                    "connection_form_schema": schema,
                }
            )
        return connectors

    @staticmethod
    def connection_form_schema(connector_type: str) -> dict:
        return _adapter_class(connector_type).get_connection_form_schema()


def _probe_dialect_name(adapter_cls: type[DataSourceAdapter]) -> str:
    """Resolve dialect via adapter without branching on connector_type."""
    schema = adapter_cls.get_connection_form_schema()
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    probe_config: dict[str, Any] = {}
    for field in required:
        prop = properties.get(field, {})
        if prop.get("type") == "integer":
            probe_config[field] = prop.get("default", 0)
        else:
            probe_config[field] = prop.get("default", "probe")
    return adapter_cls(probe_config).get_dialect_name()
