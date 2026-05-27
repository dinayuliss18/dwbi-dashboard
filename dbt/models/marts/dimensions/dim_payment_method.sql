select
    {{ generate_surrogate_key(['payment_method_id']) }} as payment_method_key,
    payment_method_id as payment_method_nk,
    payment_method_name,
    payment_group,
    case
        when payment_method_name = 'COD' then false
        else true
    end as supports_instant_voucher
from {{ ref('stg_payment_methods') }}
