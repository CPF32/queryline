"""Database engine adapters.

Concrete adapter implementations live in subpackages keyed by connector_type.
All engine-specific code is confined to this package.
"""

from app.adapters.base import (
    ConnectionTestResult,
    DataSourceAdapter,
    QueryResult,
    ReadOnlyVerificationResult,
    SchemaSnapshot,
)
from app.adapters.registry import ADAPTER_REGISTRY
from app.adapters.secrets import SecretManager, get_secret_manager

_REGISTERED = False


def ensure_adapters_registered() -> None:
    """Import adapter modules once so they register with ADAPTER_REGISTRY."""
    global _REGISTERED
    if _REGISTERED:
        return
    from app.adapters import sqlite  # noqa: F401

    for module_name in ("postgresql", "mysql", "mssql"):
        try:
            __import__(f"app.adapters.{module_name}", fromlist=[module_name])
        except ImportError:
            continue

    _REGISTERED = True


__all__ = [
    "ADAPTER_REGISTRY",
    "ConnectionTestResult",
    "DataSourceAdapter",
    "QueryResult",
    "ReadOnlyVerificationResult",
    "SchemaSnapshot",
    "SecretManager",
    "ensure_adapters_registered",
    "get_secret_manager",
]
