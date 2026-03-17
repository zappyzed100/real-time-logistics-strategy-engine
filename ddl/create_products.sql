-- 商品マスターテーブルの作成
CREATE TABLE IF NOT EXISTS products (
    product_id   INT PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    category     VARCHAR(100),
    weight_kg    FLOAT COMMENT '配送コスト計算に使用',
    unit_price   NUMBER(12, 2)
);