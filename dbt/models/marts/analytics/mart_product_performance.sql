select
    products.product_key,
    products.product_name,
    products.sku,
    categories.category_name,
    categories.subcategory_name,
    count(distinct facts.order_id) as order_count,
    count(*) as order_item_count,
    sum(facts.quantity) as quantity_sold,
    sum(facts.total_payment) as revenue,
    sum(facts.profit) as profit,
    sum(case when facts.is_returned then facts.quantity else 0 end) as returned_quantity,
    avg(case when facts.is_returned then 1.0 else 0.0 end) as return_rate,
    avg(case when facts.is_cancelled then 1.0 else 0.0 end) as cancellation_rate,
    count(distinct facts.customer_nk) as buying_customers,
    count(distinct facts.order_id)::numeric / nullif(count(distinct facts.customer_nk), 0) as repurchase_proxy_rate
from {{ ref('fct_order_item') }} as facts
inner join {{ ref('dim_product') }} as products
    on facts.product_key = products.product_key
inner join {{ ref('dim_category') }} as categories
    on facts.category_key = categories.category_key
group by
    products.product_key,
    products.product_name,
    products.sku,
    categories.category_name,
    categories.subcategory_name
