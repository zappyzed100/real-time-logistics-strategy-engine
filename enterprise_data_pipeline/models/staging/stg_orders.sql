with source as (
    select * from {{ source('raw_data', 'ORDERS') }}
),

renamed as (
    select
        "ORDER_ID" as order_id,
        "PRODUCT_ID" as product_id,
        "CUSTOMER_LAT" as customer_lat,
        "CUSTOMER_LON" as customer_lon,
        -- 文字列をタイムスタンプ型へキャスト
        cast("ORDER_DATE" as timestamp) as ordered_at
    from source
)

select * from renamed