with source as (
    select * from {{ source('raw_data', 'LOGISTICS_CENTERS') }}
),

renamed as (
    select
        "CENTER_ID" as center_id,
        "CENTER_NAME" as center_name,
        "LATITUDE" as latitude,
        "LONGITUDE" as longitude
    from source
)

select * from renamed