with candidate_costs as (
    select * from {{ ref('int_delivery_cost_candidates') }}
)

select *
from candidate_costs
qualify row_number() over (partition by order_id order by delivery_cost asc, center_name asc) = 1