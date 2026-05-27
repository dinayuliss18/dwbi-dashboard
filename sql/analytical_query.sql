-- Monthly revenue trend
select month_start_date, net_revenue, profit, profit_margin
from analytics.mart_monthly_revenue
order by month_start_date;

-- Total transactions and revenue for each city
select city_name, province, transaction_count, revenue, profit
from analytics.mart_city_performance
order by revenue desc;

-- Top 10 products by revenue and quantity sold
select product_name, category_name, quantity_sold, revenue
from analytics.mart_product_performance
order by revenue desc, quantity_sold desc
limit 10;

-- Payment methods used most frequently
select payment_method_name, transaction_count, transaction_value
from analytics.mart_payment_method_performance
order by transaction_count desc;

-- Voucher determination based on order condition
select
    voucher_code,
    voucher_name,
    voucher_type,
    rule_description,
    min_order_amount,
    discount_amount
from analytics.dim_voucher
order by voucher_nk;

-- Shipping services used most frequently
select shipping_provider, shipping_service, order_count
from analytics.mart_shipping_performance
order by order_count desc;

-- Cancelled orders for each shipping service
select shipping_provider, shipping_service, cancelled_order_count
from analytics.mart_shipping_performance
order by cancelled_order_count desc;

-- Products with highest return rates
select product_name, category_name, order_count, returned_quantity, return_rate
from analytics.mart_product_performance
where order_count >= 10
order by return_rate desc, returned_quantity desc
limit 20;

-- Total loss from discounts, shipping subsidies, vouchers, and margin impact
select
    month_start_date,
    discount_amount,
    shipping_subsidy,
    voucher_amount,
    discount_amount + shipping_subsidy + voucher_amount as total_promo_loss,
    net_revenue,
    profit,
    profit_margin
from analytics.mart_monthly_revenue
order by month_start_date;

-- Peak order hours
select hour_of_day, daypart, order_count, revenue
from analytics.mart_hourly_orders
order by order_count desc;

-- Cancellation rate and status stage where cancellation happens most frequently
select
    cancellation_stage,
    count(distinct case when is_cancelled then order_id end) as cancelled_orders,
    count(distinct order_id) as total_orders,
    count(distinct case when is_cancelled then order_id end)::numeric / nullif(count(distinct order_id), 0) as cancellation_rate
from analytics.fct_order_item
group by cancellation_stage
order by cancelled_orders desc;

-- Cancellation rate for each product
select product_name, order_count, cancellation_rate
from analytics.mart_product_performance
where order_count >= 10
order by cancellation_rate desc
limit 20;

--Payment methods with highest transaction value
select payment_method_name, transaction_value, transaction_count, avg_item_value
from analytics.mart_payment_method_performance
order by transaction_value desc;

--Number of shipping services per quarter
SELECT 
    DATE_TRUNC('quarter', d.date_day)::DATE AS "Kuartal",
    shipping.shipping_provider AS "Jasa Pengiriman",
    COUNT(DISTINCT facts.order_id) AS "Total Order"
FROM analytics.fct_order_item AS facts
INNER JOIN analytics.dim_date AS d 
    ON facts.order_date_key = d.date_key
INNER JOIN analytics.dim_shipping AS shipping
    ON facts.shipping_key = shipping.shipping_key
GROUP BY 1, 2
ORDER BY 1 ASC;

--Segmen pelanggan mana yang memiliki transaksi tertinggi
SELECT 
    c.loyalty_tier AS "Segmen Pelanggan",
    COUNT(DISTINCT facts.order_id) AS "Total Transaksi (Jumlah Order)",
    SUM(facts.total_payment) AS "Total Nilai Transaksi (IDR)"
FROM analytics.fct_order_item AS facts
INNER JOIN analytics.dim_customer AS c 
    ON facts.customer_key = c.customer_key
GROUP BY 1
ORDER BY 2 DESC;

--Berapa margin keuntungan rata-rata per kategori produk
SELECT 
    category_name AS "Kategori Produk",
    SUM(revenue) AS "Total Revenue (IDR)",
    SUM(profit) AS "Total Profit (IDR)",
    ROUND(
        (SUM(profit)::NUMERIC / NULLIF(SUM(revenue), 0)) * 100, 2
    ) AS "Margin Keuntungan Rata-rata (%)"
FROM analytics.mart_product_performance
GROUP BY 1
ORDER BY 4 DESC;