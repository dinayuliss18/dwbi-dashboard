select
    order_item_id,
    order_id,
    product_id,
    item_number,
    quantity,
    unit_price::bigint as unit_price,
    subtotal::bigint as subtotal,
    discount_amount::bigint as discount_amount,
    shipping_subsidy::bigint as shipping_subsidy,
    voucher_amount::bigint as voucher_amount,
    total_payment::bigint as total_payment,
    estimated_cost::bigint as estimated_cost,
    profit::bigint as profit,
    is_returned,
    is_cancelled,
    loaded_at
from {{ source('raw', 'order_items') }}
