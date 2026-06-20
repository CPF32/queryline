-- Retail demo schema (PostgreSQL)

CREATE TABLE regions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    country VARCHAR(50) NOT NULL
);

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    region_id INTEGER NOT NULL REFERENCES regions(id),
    joined_date DATE NOT NULL
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    order_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL,
    total_amount NUMERIC(10, 2) NOT NULL
);

CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    line_total NUMERIC(10, 2) NOT NULL
);

INSERT INTO regions (id, name, country) VALUES
    (1, 'Northwest', 'USA'),
    (2, 'Southeast', 'USA'),
    (3, 'Midwest', 'USA');
SELECT setval('regions_id_seq', (SELECT MAX(id) FROM regions));

INSERT INTO customers (id, name, email, region_id, joined_date) VALUES
    (1, 'Acme Corp', 'ops@acme.example', 1, '2024-01-10'),
    (2, 'Beta LLC', 'hello@beta.example', 2, '2024-03-15'),
    (3, 'Gamma Inc', 'team@gamma.example', 1, '2025-06-01'),
    (4, 'Delta Co', 'sales@delta.example', 3, '2025-11-20');
SELECT setval('customers_id_seq', (SELECT MAX(id) FROM customers));

INSERT INTO products (id, name, category, unit_price) VALUES
    (1, 'Widget Pro', 'Hardware', 49.99),
    (2, 'Service Plan', 'Software', 19.99),
    (3, 'Cable Pack', 'Accessories', 9.50),
    (4, 'Setup Kit', 'Services', 120.00);
SELECT setval('products_id_seq', (SELECT MAX(id) FROM products));

INSERT INTO orders (id, customer_id, order_date, status, total_amount) VALUES
    (101, 1, '2026-01-05', 'completed', 169.97),
    (102, 2, '2026-01-12', 'completed', 39.98),
    (103, 1, '2026-02-01', 'completed', 49.99),
    (104, 3, '2026-02-14', 'pending', 129.50);
SELECT setval('orders_id_seq', (SELECT MAX(id) FROM orders));

INSERT INTO order_items (id, order_id, product_id, quantity, line_total) VALUES
    (1, 101, 1, 2, 99.98),
    (2, 101, 3, 2, 19.00),
    (3, 101, 2, 1, 19.99),
    (4, 102, 2, 2, 39.98),
    (5, 103, 1, 1, 49.99),
    (6, 104, 4, 1, 120.00),
    (7, 104, 3, 1, 9.50);
SELECT setval('order_items_id_seq', (SELECT MAX(id) FROM order_items));

-- Read-only role for the app (used by Docker init)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'retail_reader') THEN
        CREATE ROLE retail_reader LOGIN PASSWORD 'retail_reader';
    END IF;
END
$$;
GRANT CONNECT ON DATABASE retail_demo TO retail_reader;
GRANT USAGE ON SCHEMA public TO retail_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO retail_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO retail_reader;
