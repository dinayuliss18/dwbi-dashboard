select
    items.order_item_id,
    items.order_id,
    orders.order_number,
    orders.customer_id,
    orders.order_ts,
    orders.order_status,
    orders.cancellation_stage,
    orders.payment_method_id,
    orders.shipping_service_id,
    orders.voucher_id,
    orders.sales_channel,
    orders.currency,
    items.product_id,
    products.category_id,
    items.item_number,
    items.quantity,
    items.unit_price,
    items.subtotal,
    items.discount_amount,
    items.shipping_subsidy,
    items.voucher_amount,
    items.total_payment,
    items.estimated_cost,
    items.profit,
    fulfillment.delivery_duration_minutes,
    items.is_returned,
    items.is_cancelled,
    fulfillment.is_delayed,
    payments.payment_status,
    payments.payment_ts,
    items.loaded_at
from {{ ref('stg_order_items') }} as items
inner join {{ ref('stg_orders') }} as orders
    on items.order_id = orders.order_id
inner join {{ ref('stg_products') }} as products
    on items.product_id = products.product_id
left join {{ ref('stg_payments') }} as payments
    on items.order_id = payments.order_id
left join {{ ref('int_order_fulfillment') }} as fulfillment
    on items.order_id = fulfillment.order_id
