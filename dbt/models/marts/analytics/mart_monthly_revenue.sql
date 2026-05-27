select
    dates.year,
    dates.month,
    date_trunc('month', dates.date_day)::date as month_start_date,
    count(distinct facts.order_id) as order_count,
    count(*) as order_item_count,
    sum(facts.quantity) as quantity_sold,
    sum(facts.subtotal) as gross_revenue,
    sum(facts.discount_amount) as discount_amount,
    sum(facts.shipping_subsidy) as shipping_subsidy,
    sum(facts.voucher_amount) as voucher_amount,
    sum(facts.total_payment) as net_revenue,
    sum(facts.estimated_cost) as estimated_cost,
    sum(facts.profit) as profit,
    sum(facts.profit) / nullif(sum(facts.total_payment), 0) as profit_margin
from {{ ref('fct_order_item') }} as facts
inner join {{ ref('dim_date') }} as dates
    on facts.order_date_key = dates.date_key
group by dates.year, dates.month, date_trunc('month', dates.date_day)::date
