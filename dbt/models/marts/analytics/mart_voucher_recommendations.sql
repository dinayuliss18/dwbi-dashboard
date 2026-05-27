select
    customer_group,
    recommended_voucher_strategy,
    count(*) as customer_count,
    avg(revenue) as avg_revenue,
    avg(transaction_count) as avg_transaction_count
from {{ ref('mart_customer_segments') }}
group by customer_group, recommended_voucher_strategy
