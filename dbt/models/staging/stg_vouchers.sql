select
    voucher_id,
    voucher_code,
    voucher_name,
    voucher_type,
    rule_description,
    min_order_amount::bigint as min_order_amount,
    discount_amount::bigint as discount_amount,
    cashback_rate::numeric(8, 4) as cashback_rate,
    loaded_at
from {{ source('raw', 'vouchers') }}
