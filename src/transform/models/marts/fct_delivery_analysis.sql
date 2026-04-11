{{ config(
    materialized='table',
    cluster_by=['prefecture', 'center_name']
) }}

with ranked_candidates as (
    select * from {{ ref('fct_delivery_candidate_rankings') }}
),

best_candidate as (
    select
        order_id,
        prefecture,
        center_name,
        delivery_cost
    from ranked_candidates
    where order_candidate_rank = 1
),

orders as (
    select * from {{ ref('stg_orders') }}
),

products as (
    select * from {{ ref('stg_products') }}
)

select *
from (
    select
        best_candidate.order_id,
        coalesce(orders.prefecture, best_candidate.prefecture) as prefecture,
        best_candidate.center_name,
        orders.customer_lat,
        orders.customer_lon,
        products.weight_kg,
        orders.quantity,
        best_candidate.delivery_cost
    from best_candidate
    inner join orders
        on best_candidate.order_id = orders.order_id
    inner join products
        on orders.product_id = products.product_id
) as delivery_analysis