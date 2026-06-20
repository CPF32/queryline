"""Admin API blueprints."""

from app.api.admin.data_sources import admin_data_sources_bp
from app.api.admin.examples import admin_examples_bp
from app.api.admin.glossary import admin_glossary_bp
from app.api.admin.llm_settings import admin_llm_settings_bp
from app.api.admin.query_log import admin_query_log_bp
from app.api.admin.schema import admin_schema_bp

__all__ = [
    "admin_data_sources_bp",
    "admin_examples_bp",
    "admin_glossary_bp",
    "admin_llm_settings_bp",
    "admin_query_log_bp",
    "admin_schema_bp",
]
