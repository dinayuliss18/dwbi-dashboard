with customer_metrics as (
    select
        customer_nk,
        count(distinct order_id) as transaction_count,
        sum(total_payment) as revenue,
        sum(profit) as profit,
        max(order_ts)::date as last_order_date
    from {{ ref('fct_order_item') }}
    group by customer_nk
)

select
    metrics.customer_nk,
    customers.customer_key as current_customer_key,
    customers.full_name,
    customers.loyalty_tier,
    cities.city_name,
    metrics.transaction_count,
    metrics.revenue,
    metrics.profit,
    metrics.last_order_date,
    case
        when metrics.revenue >= 5000000 and metrics.transaction_count >= 5 then 'VIP'
        when metrics.revenue >= 3000000 and metrics.transaction_count < 5 then 'High Revenue Low Frequency'
        when metrics.revenue < 1000000 and metrics.transaction_count >= 5 then 'Frequent Low Basket'
        when metrics.transaction_count = 1 then 'New/One-time'
        else 'Regular'
    end as customer_group,
    case
        when metrics.revenue >= 5000000 and metrics.transaction_count >= 5 then 'Exclusive loyalty voucher'
        when metrics.revenue >= 3000000 and metrics.transaction_count < 5 then 'Retention voucher'
        when metrics.revenue < 1000000 and metrics.transaction_count >= 5 then 'Basket-size upsell voucher'
        when metrics.transaction_count = 1 then 'Second purchase voucher'
        else 'Standard campaign voucher'
    end as recommended_voucher_strategy
from customer_metrics as metrics
inner join {{ ref('dim_customer') }} as customers
    on metrics.customer_nk = customers.customer_nk
    and customers.is_current
inner join {{ ref('dim_city') }} as cities
    on customers.city_key = cities.city_key
