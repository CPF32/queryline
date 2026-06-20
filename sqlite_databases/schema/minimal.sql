-- Minimal single-table dataset for quick smoke tests and connection checks.

CREATE TABLE daily_sales (
    id INTEGER PRIMARY KEY,
    sale_date TEXT NOT NULL,
    region TEXT NOT NULL,
    product TEXT NOT NULL,
    units INTEGER NOT NULL,
    revenue REAL NOT NULL
);

INSERT INTO daily_sales (id, sale_date, region, product, units, revenue) VALUES
    (1, '2026-01-01', 'North', 'Widget', 12, 600.00),
    (2, '2026-01-01', 'South', 'Widget', 8, 400.00),
    (3, '2026-01-02', 'North', 'Gadget', 5, 750.00),
    (4, '2026-01-02', 'South', 'Gadget', 3, 450.00),
    (5, '2026-01-03', 'East', 'Widget', 10, 500.00);
