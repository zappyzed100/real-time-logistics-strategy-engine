{{ config(materialized='table') }}

with ranked_candidates as (
    select * from {{ ref('fct_delivery_candidate_rankings') }}
)

select *
from ranked_candidates
where order_candidate_rank = 1