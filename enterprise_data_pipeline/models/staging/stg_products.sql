with source as (
    select * from {{ source('raw_data', 'PRODUCTS') }}
),

renamed as (
    select
        try_to_number("PRODUCT_ID") as product_id,
        "PRODUCT_NAME" as product_name,
        try_to_double("WEIGHT_KG") as weight_kg
    from source
),

deduped as (
    select
        *,
        row_number() over (
            partition by product_id
            order by product_name
        ) as _rn
    from renamed
)

select
    product_id,
    product_name,
    weight_kg
from deduped
where _rn = 1