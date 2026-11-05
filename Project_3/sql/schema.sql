CREATE TABLE products(
    product_id VARCHAR(10) PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NULL,
    unit_price DECIMAL(12,2) NOT NULL,
    stock_qty INT NOT NULL,
    last_loaded_date DATE NOT NULL,

    CHECK (unit_price > 0),
    CHECK (stock_qty >= 0)
) ENGINE = InnoDB;

CREATE TABLE sales(
    sale_id VARCHAR(20) PRIMARY KEY,
    customer_id VARCHAR(20) NULL,
    city VARCHAR(50) NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(12,2) NOT NULL,
    total_amount DECIMAL(14,2) NOT NULL,
    payment_method VARCHAR(20) NULL,
    sold_at DATETIME NOT NULL,
    load_date DATE NOT NULL,

    CHECK (product_id > 0),
    FOREIGN KEY (product_id) REFERENCES products(product_id)

) ENGINE = InnoDB;

CREATE TABLE pipline_runs(
    run_id INT AUTO_INCREMENT PRIMARY KEY,
    run_date DATETIME NOT NULL,
    started_at DATETIME NOT NULL,
    finished_at DATETIME NOT NULL,
    status VARCHAR(10) NOT NULL,
    products_upserted INT NOT NULL,
    sales_inserted INT NOT NULL,
    rejected_total INT NOT NULL

) ENGINE = InnoDB;