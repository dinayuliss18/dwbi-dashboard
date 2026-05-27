select
    shipping_service_id,
    shipping_provider,
    shipping_service,
    service_level,
    min_delivery_days,
    max_delivery_days,
    loaded_at
from {{ source('raw', 'shipping_services') }}
