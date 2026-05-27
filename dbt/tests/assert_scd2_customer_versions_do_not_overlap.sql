select
    left_side.customer_nk,
    left_side.customer_key as left_customer_key,
    right_side.customer_key as right_customer_key
from {{ ref('dim_customer') }} as left_side
inner join {{ ref('dim_customer') }} as right_side
    on left_side.customer_nk = right_side.customer_nk
    and left_side.customer_key <> right_side.customer_key
    and left_side.valid_from < right_side.valid_to
    and right_side.valid_from < left_side.valid_to
