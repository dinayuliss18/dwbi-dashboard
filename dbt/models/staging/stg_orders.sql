select
    order_id,
    order_number,
    customer_id,
    order_ts,
    order_status,
    cancellation_stage,
    payment_method_id,
    shipping_service_id,
    voucher_id,
    sales_channel,
    currency,
    loaded_at
from {{ source('raw', 'orders') }}
