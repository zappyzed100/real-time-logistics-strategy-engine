with source as (
    select * from {{ source('raw_data', 'ORDERS') }}
),

renamed as (
    select
        try_to_number("ORDER_ID") as order_id,
        try_to_number("PRODUCT_ID") as product_id,
        try_to_number("QUANTITY") as quantity,
        try_to_double("CUSTOMER_LAT") as customer_lat,
        try_to_double("CUSTOMER_LON") as customer_lon,
        -- Bronze 層は文字列受けなので Silver で型を揃える
        try_to_timestamp_ntz("ORDER_DATE") as ordered_at
    from source
),

deduped as (
    select
        *,
        row_number() over (
            partition by order_id
            order by ordered_at desc nulls last
        ) as _rn
    from renamed
)

select
    order_id,
    product_id,
    quantity,
    customer_lat,
    customer_lon,
    ordered_at
from deduped
where _rn = 1