-- 注文履歴テーブルの作成
CREATE TABLE IF NOT EXISTS orders (
    order_id     INT PRIMARY KEY,
    product_id   INT REFERENCES products(product_id),
    quantity     INT NOT NULL,
    customer_lat FLOAT NOT NULL,
    customer_lon FLOAT NOT NULL,
    order_date   DATE DEFAULT CURRENT_DATE()
);