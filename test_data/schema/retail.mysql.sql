-- Retail demo schema (MySQL / MariaDB)

CREATE TABLE regions (
    id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    country VARCHAR(50) NOT NULL
);

CREATE TABLE customers (
    id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    region_id INT NOT NULL,
    joined_date DATE NOT NULL,
    FOREIGN KEY (region_id) REFERENCES regions(id)
);

CREATE TABLE products (
    id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL
);

CREATE TABLE orders (
    id INT PRIMARY KEY,
    customer_id INT NOT NULL,
    order_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE order_items (
    id INT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    line_total DECIMAL(10, 2) NOT NULL,
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

CREATE USER IF NOT EXISTS 'retail_reader'@'%' IDENTIFIED BY 'retail_reader';
GRANT SELECT ON retail_demo.* TO 'retail_reader'@'%';
FLUSH PRIVILEGES;
