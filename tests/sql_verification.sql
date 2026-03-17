-- 1. レコード件数の確認（期待値通りか）
SELECT 'products' as table_name, count(*) as cnt FROM products
UNION ALL
SELECT 'logistics_centers', count(*) FROM logistics_centers
UNION ALL
SELECT 'orders', count(*) FROM orders
UNION ALL
SELECT 'inventory', count(*) FROM inventory;

-- 2. リレーション（JOIN）の確認
-- 注文データに商品の重量(weight_kg)が正しく紐付くか
SELECT 
    o.order_id,
    p.product_name,
    p.weight_kg,
    o.quantity,
    (p.weight_kg * o.quantity) as total_weight
FROM orders o
JOIN products p ON o.product_id = p.product_id;

-- 3. 在庫集計の確認
-- 倉庫別の在庫合計数を確認
SELECT 
    lc.center_name,
    SUM(i.stock_quantity) as total_stock
FROM inventory i
JOIN logistics_centers lc ON i.center_id = lc.center_id
GROUP BY lc.center_name;