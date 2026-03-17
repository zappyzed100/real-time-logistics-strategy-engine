-- 倉庫別在庫テーブルの作成
CREATE TABLE IF NOT EXISTS inventory (
    center_id      INT REFERENCES logistics_centers(center_id),
    product_id     INT REFERENCES products(product_id),
    stock_quantity INT NOT NULL,
    PRIMARY KEY (center_id, product_id)
);