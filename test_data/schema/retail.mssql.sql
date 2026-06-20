-- Retail demo schema (SQL Server)

CREATE TABLE regions (
    id INT PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    country NVARCHAR(50) NOT NULL
);

CREATE TABLE customers (
    id INT PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    email NVARCHAR(150) NOT NULL,
    region_id INT NOT NULL,
    joined_date DATE NOT NULL,
    FOREIGN KEY (region_id) REFERENCES regions(id)
);

CREATE TABLE products (
    id INT PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    category NVARCHAR(50) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL
);

CREATE TABLE orders (
    id INT PRIMARY KEY,
    customer_id INT NOT NULL,
    order_date DATE NOT NULL,
    status NVARCHAR(20) NOT NULL,
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
GO

INSERT INTO regions (id, name, country) VALUES
    (1, N'Northwest', N'USA'),
    (2, N'Southeast', N'USA'),
    (3, N'Midwest', N'USA');

INSERT INTO customers (id, name, email, region_id, joined_date) VALUES
    (1, N'Acme Corp', N'ops@acme.example', 1, '2024-01-10'),
    (2, N'Beta LLC', N'hello@beta.example', 2, '2024-03-15'),
    (3, N'Gamma Inc', N'team@gamma.example', 1, '2025-06-01'),
    (4, N'Delta Co', N'sales@delta.example', 3, '2025-11-20');

INSERT INTO products (id, name, category, unit_price) VALUES
    (1, N'Widget Pro', N'Hardware', 49.99),
    (2, N'Service Plan', N'Software', 19.99),
    (3, N'Cable Pack', N'Accessories', 9.50),
    (4, N'Setup Kit', N'Services', 120.00);

INSERT INTO orders (id, customer_id, order_date, status, total_amount) VALUES
    (101, 1, '2026-01-05', N'completed', 169.97),
    (102, 2, '2026-01-12', N'completed', 39.98),
    (103, 1, '2026-02-01', N'completed', 49.99),
    (104, 3, '2026-02-14', N'pending', 129.50);

INSERT INTO order_items (id, order_id, product_id, quantity, line_total) VALUES
    (1, 101, 1, 2, 99.98),
    (2, 101, 3, 2, 19.00),
    (3, 101, 2, 1, 19.99),
    (4, 102, 2, 2, 39.98),
    (5, 103, 1, 1, 49.99),
    (6, 104, 4, 1, 120.00),
    (7, 104, 3, 1, 9.50);
GO

IF NOT EXISTS (SELECT name FROM sys.server_principals WHERE name = 'retail_reader')
    CREATE LOGIN retail_reader WITH PASSWORD = 'Retail_Reader1!', CHECK_POLICY = OFF;
GO
IF NOT EXISTS (SELECT name FROM sys.database_principals WHERE name = 'retail_reader')
    CREATE USER retail_reader FOR LOGIN retail_reader;
GO
GRANT SELECT ON SCHEMA::dbo TO retail_reader;
GO
