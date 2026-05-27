select
    cities.city_name,
    cities.province,
    cities.region,
    count(distinct facts.order_id) as transaction_count,
    count(distinct facts.customer_nk) as customer_count,
    sum(facts.total_payment) as revenue,
    sum(facts.profit) as profit,
    avg(facts.delivery_duration_minutes) as avg_delivery_duration_minutes,
    avg(case when facts.is_cancelled then 1.0 else 0.0 end) as cancellation_rate
from {{ ref('fct_order_item') }} as facts
inner join {{ ref('dim_city') }} as cities
    on facts.customer_city_key = cities.city_key
group by cities.city_name, cities.province, cities.region
