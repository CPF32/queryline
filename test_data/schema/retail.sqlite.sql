-- Retail demo schema (SQLite). Five related tables with short dummy data.

CREATE TABLE regions (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT NOT NULL
);

CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    region_id INTEGER NOT NULL,
    joined_date TEXT NOT NULL,
    FOREIGN KEY (region_id) REFERENCES regions(id)
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_price REAL NOT NULL
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    status TEXT NOT NULL,
    total_amount REAL NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    line_total REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

INSERT INTO regions (id, name, country) VALUES
    (1, 'Northwest', 'USA'),
    (2, 'Southeast', 'USA'),
    (3, 'Midwest', 'USA');

INSERT INTO customers (id, name, email, region_id, joined_date) VALUES
    (1, 'Acme Corp', 'ops@acme.example', 1, '2024-01-10'),
    (2, 'Beta LLC', 'hello@beta.example', 2, '2024-03-15'),
    (3, 'Gamma Inc', 'team@gamma.example', 1, '2025-06-01'),
    (4, 'Delta Co', 'sales@delta.example', 3, '2025-11-20');

INSERT INTO products (id, name, category, unit_price) VALUES
    (1, 'Widget Pro', 'Hardware', 49.99),
    (2, 'Service Plan', 'Software', 19.99),
    (3, 'Cable Pack', 'Accessories', 9.50),
    (4, 'Setup Kit', 'Services', 120.00);

INSERT INTO orders (id, customer_id, order_date, status, total_amount) VALUES
    (101, 1, '2026-01-05', 'completed', 169.97),
    (102, 2, '2026-01-12', 'completed', 39.98),
    (103, 1, '2026-02-01', 'completed', 49.99),
    (104, 3, '2026-02-14', 'pending', 129.50);

INSERT INTO order_items (id, order_id, product_id, quantity, line_total) VALUES
    (1, 101, 1, 2, 99.98),
    (2, 101, 3, 2, 19.00),
    (3, 101, 2, 1, 19.99),
    (4, 102, 2, 2, 39.98),
    (5, 103, 1, 1, 49.99),
    (6, 104, 4, 1, 120.00),
    (7, 104, 3, 1, 9.50);
