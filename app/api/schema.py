"""Schema import and metadata REST endpoints.

Endpoints:
    POST   /api/v1/data-sources/{data_source_id}/schema/import
    GET    /api/v1/data-sources/{data_source_id}/schema/tables
    GET    /api/v1/data-sources/{data_source_id}/schema/tables/{id}
    PUT    /api/v1/data-sources/{data_source_id}/schema/tables/{id}
    DELETE /api/v1/data-sources/{data_source_id}/schema/tables/{id}
    GET    /api/v1/data-sources/{data_source_id}/schema/tables/{table_id}/columns
    PUT    /api/v1/data-sources/{data_source_id}/schema/columns/{id}
    GET    /api/v1/data-sources/{data_source_id}/schema/relationships
    DELETE /api/v1/data-sources/{data_source_id}/schema/relationships/{id}

See CONTRACTS.md §5.4–§5.5.
"""
