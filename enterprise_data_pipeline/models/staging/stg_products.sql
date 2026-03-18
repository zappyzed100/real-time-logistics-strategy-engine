with source as (
    select * from {{ source('raw_data', 'PRODUCTS') }}
),

renamed as (
    select
        "PRODUCT_ID" as product_id,
        "PRODUCT_NAME" as product_name,
        "WEIGHT_KG" as weight_kg
    from source
)

select * from renamed