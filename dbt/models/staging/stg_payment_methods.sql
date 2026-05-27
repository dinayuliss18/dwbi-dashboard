select
    payment_method_id,
    payment_method_name,
    payment_group,
    loaded_at
from {{ source('raw', 'payment_methods') }}
