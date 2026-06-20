-- Simple analytics schema: four tables, region denormalized on customers.
-- Good for basic counts, sums, and the integration smoke-test flow.

CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    region TEXT NOT NULL
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    amount REAL NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

INSERT INTO customers (id, name, region) VALUES
    (1, 'Acme Corp', 'North'),
    (2, 'Beta LLC', 'South'),
    (3, 'Gamma Inc', 'North');

INSERT INTO products (id, name, category) VALUES
    (1, 'Widget', 'Hardware'),
    (2, 'Service Plan', 'Software');

INSERT INTO orders (id, customer_id, order_date, amount) VALUES
    (1, 1, '2026-01-15', 150.0),
    (2, 1, '2026-02-10', 75.0),
    (3, 2, '2026-01-20', 200.0),
    (4, 3, '2026-03-01', 50.0);

INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) VALUES
    (1, 1, 1, 2, 50.0),
    (2, 2, 2, 1, 75.0),
    (3, 3, 1, 4, 50.0),
    (4, 4, 2, 1, 50.0);
