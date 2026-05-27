select
    {{ generate_surrogate_key(['shipping_service_id']) }} as shipping_key,
    shipping_service_id as shipping_service_nk,
    shipping_provider,
    shipping_service,
    service_level,
    min_delivery_days,
    max_delivery_days
from {{ ref('stg_shipping_services') }}
