-- 配送拠点（倉庫）テーブルの作成
CREATE TABLE IF NOT EXISTS logistics_centers (
    center_id   INT PRIMARY KEY,
    center_name VARCHAR(255) NOT NULL,
    latitude    FLOAT NOT NULL,
    longitude   FLOAT NOT NULL
);