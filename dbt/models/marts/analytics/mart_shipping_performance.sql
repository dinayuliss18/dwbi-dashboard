select
    shipping.shipping_provider,
    shipping.shipping_service,
    shipping.service_level,
    count(distinct facts.order_id) as order_count,
    sum(case when facts.is_cancelled then 1 else 0 end) as cancelled_order_item_count,
    count(distinct case when facts.is_cancelled then facts.order_id end) as cancelled_order_count,
    avg(facts.delivery_duration_minutes) as avg_delivery_duration_minutes,
    min(facts.delivery_duration_minutes) as fastest_delivery_minutes,
    max(facts.delivery_duration_minutes) as slowest_delivery_minutes,
    avg(case when facts.is_delayed then 1.0 else 0.0 end) as delay_rate
from {{ ref('fct_order_item') }} as facts
inner join {{ ref('dim_shipping') }} as shipping
    on facts.shipping_key = shipping.shipping_key
group by shipping.shipping_provider, shipping.shipping_service, shipping.service_level
