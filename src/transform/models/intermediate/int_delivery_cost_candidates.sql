with orders as (
    select * from {{ ref('stg_orders') }}
),

products as (
    select * from {{ ref('stg_products') }}
),

centers as (
    select * from {{ ref('stg_logistics_centers') }}
),

shipping_costs as (
    select * from {{ ref('stg_shipping_costs') }}
),

candidate_costs as (
    select
        o.order_id,
        o.prefecture,
        c.center_id,
        c.center_name,
        (
            6371 * 2 * asin(
                sqrt(
                    power(sin(radians((o.customer_lat - c.latitude) / 2)), 2) +
                    cos(radians(c.latitude)) * cos(radians(o.customer_lat)) *
                    power(sin(radians((o.customer_lon - c.longitude) / 2)), 2)
                )
            )
        ) as distance_km,
        p.weight_kg * o.quantity as total_weight_kg,
        round(
            (
                600
                + (
                    (
                        6371 * 2 * asin(
                            sqrt(
                                power(sin(radians((o.customer_lat - c.latitude) / 2)), 2) +
                                cos(radians(c.latitude)) * cos(radians(o.customer_lat)) *
                                power(sin(radians((o.customer_lon - c.longitude) / 2)), 2)
                            )
                        )
                    ) * 12
                )
            )
            * sc.shipping_cost
            * (
                1 + least(power(p.weight_kg * o.quantity, 0.6) / 12, 1.2)
            ),
            2
        ) as delivery_cost
    from orders o
    join products p on o.product_id = p.product_id
    cross join centers c
    join shipping_costs sc on c.center_id = sc.center_id
    where o.order_id is not null
      and p.weight_kg is not null
      and o.quantity is not null
      and sc.shipping_cost is not null
      and o.customer_lat is not null
      and o.customer_lon is not null
      and c.latitude is not null
      and c.longitude is not null
)

select * from candidate_costs
