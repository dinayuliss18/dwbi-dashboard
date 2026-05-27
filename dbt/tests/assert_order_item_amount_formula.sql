select
    order_item_id,
    subtotal,
    discount_amount,
    voucher_amount,
    total_payment
from {{ ref('fct_order_item') }}
where abs(total_payment - (subtotal - discount_amount - voucher_amount)) > 0.01
