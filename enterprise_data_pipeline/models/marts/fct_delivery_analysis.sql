with orders as (
    select * from {{ ref('stg_orders') }}
),

products as (
    select * from {{ ref('stg_products') }}
),

centers as (
    select * from {{ ref('stg_logistics_centers') }}
),

calculated as (
    select
        o.order_id,
        o.ordered_at,
        p.product_name,
        p.weight_kg,
        c.center_name,
        -- Snowpark UDF を呼び出してコストを計算
        CALCULATE_DELIVERY_COST(
            c.latitude,
            c.longitude,
            o.customer_lat,
            o.customer_lon,
            p.weight_kg
        ) as delivery_cost
    from orders o
    join products p on o.product_id = p.product_id
    cross join centers c -- 全ての注文と全拠点の組み合わせを作成
)

select * from calculated
-- 注文(order_id)ごとに、配送コスト(delivery_cost)が最小の1行だけを選択
qualify row_number() over (partition by order_id order by delivery_cost asc) = 1