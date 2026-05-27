select
    {{ generate_surrogate_key(['voucher_id']) }} as voucher_key,
    voucher_id as voucher_nk,
    voucher_code,
    voucher_name,
    voucher_type,
    rule_description,
    min_order_amount,
    discount_amount,
    cashback_rate,
    voucher_code <> 'NO_DISCOUNT' as is_voucher
from {{ ref('stg_vouchers') }}
