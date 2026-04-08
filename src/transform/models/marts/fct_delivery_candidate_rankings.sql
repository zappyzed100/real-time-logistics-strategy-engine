{{ config(materialized='table') }}

with candidate_costs as (
    select * from {{ ref('int_delivery_cost_candidates') }}
)

select
    candidate_costs.*,
    row_number() over (
        partition by center_id
        order by delivery_cost asc, distance_km asc, order_id asc
    ) as center_candidate_rank,
    row_number() over (
        partition by order_id
        order by delivery_cost asc, distance_km asc, center_name asc, center_id asc
    ) as order_candidate_rank
from candidate_costs