select
    order_item_id,
    total_payment,
    estimated_cost,
    shipping_subsidy,
    profit
from {{ ref('fct_order_item') }}
where abs(profit - (total_payment - estimated_cost - shipping_subsidy)) > 0.01
