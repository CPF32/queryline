-- Inventory / warehouse schema: nullable fields, status enums, and stock levels.
-- Good for filtering, NULL handling, and low-stock alerts.

CREATE TABLE warehouses (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    city TEXT NOT NULL,
    state TEXT NOT NULL
);

CREATE TABLE skus (
    id INTEGER PRIMARY KEY,
    sku_code TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    unit_cost REAL NOT NULL,
    reorder_level INTEGER
);

CREATE TABLE stock_levels (
    id INTEGER PRIMARY KEY,
    warehouse_id INTEGER NOT NULL,
    sku_id INTEGER NOT NULL,
    quantity_on_hand INTEGER NOT NULL,
    last_counted_at TEXT,
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id),
    FOREIGN KEY (sku_id) REFERENCES skus(id)
);

INSERT INTO warehouses (id, code, city, state) VALUES
    (1, 'WH-NYC', 'New York', 'NY'),
    (2, 'WH-CHI', 'Chicago', 'IL'),
    (3, 'WH-LAX', 'Los Angeles', 'CA');

INSERT INTO skus (id, sku_code, description, unit_cost, reorder_level) VALUES
    (1, 'WDG-001', 'Standard Widget', 12.50, 50),
    (2, 'GDG-002', 'Premium Gadget', 45.00, 20),
    (3, 'CBL-010', 'Cable 2m', 3.25, 100),
    (4, 'SRV-100', 'Setup Service', 80.00, NULL);

INSERT INTO stock_levels (id, warehouse_id, sku_id, quantity_on_hand, last_counted_at) VALUES
    (1, 1, 1, 120, '2026-02-01'),
    (2, 1, 2, 15, '2026-02-01'),
    (3, 1, 3, 8, '2026-02-01'),
    (4, 2, 1, 45, '2026-01-28'),
    (5, 2, 2, 0, '2026-01-28'),
    (6, 2, 4, 5, NULL),
    (7, 3, 1, 200, '2026-02-10'),
    (8, 3, 3, 250, '2026-02-10');
