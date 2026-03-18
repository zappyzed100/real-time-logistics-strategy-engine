with orders as (
    select * from {{ ref('stg_orders') }}
),

products as (
    select * from {{ ref('stg_products') }}
),

centers as (
    select * from {{ ref('stg_logistics_centers') }}
),

final as (
    select
        o.order_id,
        o.ordered_at,
        p.product_name,
        p.weight_kg,
        c.center_name,
        -- ここで以前作成した Snowpark UDF を呼び出す
        -- 引数: (拠点の緯度, 拠点の経度, 顧客の緯度, 顧客の経度, 商品重量)
        CALCULATE_DELIVERY_COST(
            c.latitude,
            c.longitude,
            o.customer_lat,
            o.customer_lon,
            p.weight_kg
        ) as delivery_cost
    from orders o
    join products p on o.product_id = p.product_id
    -- 今回は簡易化のため、全注文を特定の拠点（例: CENTER_ID=1）に紐付けるか、
    -- 実際のロジックに合わせて JOIN してください
    cross join centers c
)

select * from final