-- 1. レコード件数の確認（期待値通りか）
SELECT 'products' as table_name, count(*) as cnt FROM products
UNION ALL
SELECT 'logistics_centers', count(*) FROM logistics_centers
UNION ALL
SELECT 'orders', count(*) FROM orders
UNION ALL
SELECT 'shipping_costs', count(*) FROM shipping_costs;

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

-- 3. 配送コスト seed の確認
-- 配送センターごとの shipping_cost を確認
SELECT 
    lc.center_name,
    CAST(sc.shipping_cost AS FLOAT) as shipping_cost
FROM shipping_costs sc
JOIN logistics_centers lc ON sc.center_id = lc.center_id
ORDER BY shipping_cost DESC, lc.center_name;