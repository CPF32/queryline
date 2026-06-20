"""Adapter registry mapping connector_type to adapter classes.

See CONTRACTS.md §3.4. Concrete adapter modules register themselves here
at import time.
"""

from app.adapters.base import DataSourceAdapter

ADAPTER_REGISTRY: dict[str, type[DataSourceAdapter]] = {}


def register_adapter(connector_type: str, adapter_cls: type[DataSourceAdapter]) -> None:
    ADAPTER_REGISTRY[connector_type] = adapter_cls
