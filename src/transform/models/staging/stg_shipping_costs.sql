with source as (
    select * from {{ source('raw_data', 'SHIPPING_COSTS') }}
),

renamed as (
    select
        try_to_number("CENTER_ID") as center_id,
        "CENTER_NAME" as center_name,
        try_to_double("SHIPPING_COST") as shipping_cost
    from source
),

deduped as (
    select
        *,
        row_number() over (
            partition by center_id
            order by center_name
        ) as _rn
    from renamed
)

select
    center_id,
    center_name,
    shipping_cost
from deduped
where _rn = 1