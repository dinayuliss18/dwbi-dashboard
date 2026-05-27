select
    orders.order_id,
    orders.order_ts,
    shipments.checkout_ts,
    shipments.shipped_ts,
    shipments.delivered_ts,
    shipments.shipping_service_id,
    shipments.shipping_fee,
    shipments.shipping_subsidy as shipment_shipping_subsidy,
    shipments.is_delayed,
    shipments.shipping_status,
    case
        when shipments.delivered_ts is not null
            then extract(epoch from (shipments.delivered_ts - shipments.checkout_ts)) / 60.0
    end as delivery_duration_minutes,
    case
        when shipments.shipped_ts is not null
            then extract(epoch from (shipments.shipped_ts - shipments.checkout_ts)) / 60.0
    end as checkout_to_ship_minutes
from {{ ref('stg_orders') }} as orders
left join {{ ref('stg_shipments') }} as shipments
    on orders.order_id = shipments.order_id
