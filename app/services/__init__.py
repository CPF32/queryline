"""Service layer exports."""

__all__ = [
    "chart_spec_service",
    "data_source_service",
    "examples_service",
    "glossary_service",
    "metadata_service",
    "query_log_service",
    "schema_service",
]


def __getattr__(name: str):
    import importlib

    if name in __all__:
        return importlib.import_module(f"app.services.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
