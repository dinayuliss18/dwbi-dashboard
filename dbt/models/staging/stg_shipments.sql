select
    shipment_id,
    order_id,
    shipping_service_id,
    checkout_ts,
    shipped_ts,
    delivered_ts,
    shipping_fee::bigint as shipping_fee,
    shipping_subsidy::bigint as shipping_subsidy,
    is_delayed,
    shipping_status,
    tracking_number,
    loaded_at
from {{ source('raw', 'shipments') }}
