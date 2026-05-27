select
    payment_id,
    order_id,
    payment_ts,
    payment_method_id,
    payment_status,
    payment_amount::bigint as payment_amount,
    transaction_reference,
    loaded_at
from {{ source('raw', 'payments') }}
