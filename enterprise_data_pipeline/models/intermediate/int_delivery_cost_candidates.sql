with orders as (
    select * from {{ ref('stg_orders') }}
),

products as (
    select * from {{ ref('stg_products') }}
),

centers as (
    select * from {{ ref('stg_logistics_centers') }}
),

candidate_costs as (
    select
        o.order_id,
        o.ordered_at,
        o.quantity,
        p.product_name,
        p.weight_kg,
        c.center_name,
        o.customer_lat,
        o.customer_lon,
        c.latitude as center_lat,
        c.longitude as center_lon,
        round(
            (
                6371 * 2 * asin(
                    sqrt(
                        power(sin(radians((o.customer_lat - c.latitude) / 2)), 2) +
                        cos(radians(c.latitude)) * cos(radians(o.customer_lat)) *
                        power(sin(radians((o.customer_lon - c.longitude) / 2)), 2)
                    )
                )
            ) * (p.weight_kg * o.quantity) * 10.0,
            2
        ) as delivery_cost
    from orders o
    join products p on o.product_id = p.product_id
    cross join centers c
    where o.order_id is not null
      and p.weight_kg is not null
      and o.quantity is not null
      and o.customer_lat is not null
      and o.customer_lon is not null
      and c.latitude is not null
      and c.longitude is not null
)

select * from candidate_costs
