select
    {{ generate_surrogate_key(['is_cancelled', 'is_returned', 'has_voucher', 'has_shipping_subsidy', 'is_delayed', 'cancellation_stage']) }} as order_flags_key,
    is_cancelled,
    is_returned,
    has_voucher,
    has_shipping_subsidy,
    is_delayed,
    cancellation_stage
from (
    select distinct
        is_cancelled,
        is_returned,
        voucher_amount > 0 as has_voucher,
        shipping_subsidy > 0 as has_shipping_subsidy,
        coalesce(is_delayed, false) as is_delayed,
        coalesce(cancellation_stage, 'not_cancelled') as cancellation_stage
    from {{ ref('int_order_item_enriched') }}
) as flags
