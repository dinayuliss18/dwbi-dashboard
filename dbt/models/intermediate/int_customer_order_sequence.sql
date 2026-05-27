select
    order_id,
    customer_id,
    order_ts,
    row_number() over (partition by customer_id order by order_ts, order_id) as customer_order_number,
    min(order_ts) over (partition by customer_id) as first_order_ts
from {{ ref('stg_orders') }}
