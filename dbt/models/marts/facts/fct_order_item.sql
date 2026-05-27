{{ config(
    materialized='incremental',
    unique_key='order_item_id',
    incremental_strategy='merge',
    tags=['incremental']
) }}

select
    {{ generate_surrogate_key(['items.order_item_id']) }} as order_item_key,
    items.order_item_id,
    items.order_id,
    items.order_number,
    items.item_number,

    to_char(items.order_ts::date, 'YYYYMMDD')::integer as order_date_key,

    (
        extract(hour from items.order_ts)::integer * 60
        + extract(minute from items.order_ts)::integer
    ) as order_time_key,

    case
        when items.payment_ts is not null then
            to_char(items.payment_ts::date, 'YYYYMMDD')::integer
    end as payment_date_key,

    customers.customer_key,
    customers.city_key as customer_city_key,
    products.product_key,
    categories.category_key,
    payment_methods.payment_method_key,
    shipping.shipping_key,
    statuses.order_status_key,
    vouchers.voucher_key,
    flags.order_flags_key,

    items.customer_id as customer_nk,
    items.product_id as product_nk,

    items.order_ts,
    items.sales_channel,
    items.currency,
    items.payment_status,
    items.cancellation_stage,

    items.quantity,
    items.unit_price,
    items.subtotal,
    items.discount_amount,
    items.shipping_subsidy,
    items.voucher_amount,
    items.total_payment,
    items.estimated_cost,
    items.profit,

    items.delivery_duration_minutes,

    items.is_returned,
    items.is_cancelled,

    coalesce(items.is_delayed, false) as is_delayed,

    sequence.customer_order_number,

    sequence.customer_order_number = 1
        as is_new_customer_order,

    items.loaded_at

from {{ ref('int_order_item_enriched') }} as items

inner join {{ ref('dim_customer') }} as customers
    on items.customer_id = customers.customer_nk
    and items.order_ts >= customers.valid_from
    and items.order_ts < customers.valid_to

inner join {{ ref('dim_product') }} as products
    on items.product_id = products.product_nk

inner join {{ ref('dim_category') }} as categories
    on items.category_id = categories.category_nk

inner join {{ ref('dim_payment_method') }} as payment_methods
    on items.payment_method_id = payment_methods.payment_method_nk

inner join {{ ref('dim_shipping') }} as shipping
    on items.shipping_service_id = shipping.shipping_service_nk

inner join {{ ref('dim_order_status') }} as statuses
    on items.order_status = statuses.order_status

inner join {{ ref('dim_voucher') }} as vouchers
    on items.voucher_id = vouchers.voucher_nk

inner join {{ ref('dim_order_flags') }} as flags
    on items.is_cancelled = flags.is_cancelled
    and items.is_returned = flags.is_returned
    and (items.voucher_amount > 0) = flags.has_voucher
    and (items.shipping_subsidy > 0) = flags.has_shipping_subsidy
    and coalesce(items.is_delayed, false) = flags.is_delayed
    and coalesce(items.cancellation_stage, 'not_cancelled')
        = flags.cancellation_stage

left join {{ ref('int_customer_order_sequence') }} as sequence
    on items.order_id = sequence.order_id

{% if is_incremental() %}

where items.loaded_at >
(
    select coalesce(
        max(t.loaded_at),
        timestamp '1970-01-01'
    )
    from {{ this }} as t
)

{% endif %}