-- HR / payroll schema: different vocabulary from retail demos.
-- Good for testing domain-specific questions and salary aggregations.

CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    cost_center TEXT NOT NULL
);

CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    department_id INTEGER NOT NULL,
    hire_date TEXT NOT NULL,
    job_title TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);

CREATE TABLE salaries (
    id INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL,
    effective_date TEXT NOT NULL,
    annual_salary REAL NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

INSERT INTO departments (id, name, cost_center) VALUES
    (1, 'Engineering', 'CC-100'),
    (2, 'Sales', 'CC-200'),
    (3, 'Support', 'CC-300');

INSERT INTO employees (id, full_name, email, department_id, hire_date, job_title, is_active) VALUES
    (1, 'Alex Rivera', 'alex@example.com', 1, '2022-03-01', 'Senior Engineer', 1),
    (2, 'Jordan Lee', 'jordan@example.com', 1, '2023-07-15', 'Engineer', 1),
    (3, 'Sam Patel', 'sam@example.com', 2, '2021-11-20', 'Account Executive', 1),
    (4, 'Taylor Kim', 'taylor@example.com', 3, '2024-01-10', 'Support Specialist', 1),
    (5, 'Casey Morgan', 'casey@example.com', 2, '2020-05-01', 'Sales Manager', 0);

INSERT INTO salaries (id, employee_id, effective_date, annual_salary) VALUES
    (1, 1, '2024-01-01', 145000.0),
    (2, 2, '2024-01-01', 110000.0),
    (3, 3, '2024-01-01', 95000.0),
    (4, 4, '2024-01-01', 72000.0),
    (5, 5, '2023-01-01', 125000.0);
