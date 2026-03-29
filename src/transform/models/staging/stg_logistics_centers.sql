with source as (
    select * from {{ source('raw_data', 'LOGISTICS_CENTERS') }}
),

renamed as (
    select
        try_to_number("CENTER_ID") as center_id,
        "CENTER_NAME" as center_name,
        try_to_double("LATITUDE") as latitude,
        try_to_double("LONGITUDE") as longitude
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
    latitude,
    longitude
from deduped
where _rn = 1