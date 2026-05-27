select
    times.hour_of_day,
    times.daypart,
    count(distinct facts.order_id) as order_count,
    sum(facts.total_payment) as revenue
from {{ ref('fct_order_item') }} as facts
inner join {{ ref('dim_time') }} as times
    on facts.order_time_key = times.time_key
group by times.hour_of_day, times.daypart
