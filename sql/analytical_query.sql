-- 1. Monthly revenue trend
select month_start_date, net_revenue, profit, profit_margin
from analytics.mart_monthly_revenue
order by month_start_date;

-- 2. Total transactions and revenue for each city
select city_name, province, transaction_count, revenue, profit
from analytics.mart_city_performance
order by revenue desc;

-- 3. Top 10 products by revenue and quantity sold
select product_name, category_name, quantity_sold, revenue
from analytics.mart_product_performance
order by revenue desc, quantity_sold desc
limit 10;

-- 4. Payment methods used most frequently
select payment_method_name, transaction_count, transaction_value
from analytics.mart_payment_method_performance
order by transaction_count desc;

-- 5. Voucher determination based on order condition
select
    voucher_code,
    voucher_name,
    voucher_type,
    rule_description,
    min_order_amount,
    discount_amount,
    cashback_rate
from analytics.dim_voucher
order by voucher_nk;

-- 6. Shipping services used most frequently
select shipping_provider, shipping_service, order_count
from analytics.mart_shipping_performance
order by order_count desc;

-- 7. Cancelled orders for each shipping service
select shipping_provider, shipping_service, cancelled_order_count
from analytics.mart_shipping_performance
order by cancelled_order_count desc;

-- 8. Fastest and slowest shipping services
select shipping_provider, shipping_service, avg_delivery_duration_minutes, fastest_delivery_minutes, slowest_delivery_minutes
from analytics.mart_shipping_performance
where avg_delivery_duration_minutes is not null
order by avg_delivery_duration_minutes;

-- 9. Customer groups by revenue and transaction frequency
select customer_group, count(*) as customer_count, avg(revenue) as avg_revenue, avg(transaction_count) as avg_transactions
from analytics.mart_customer_segments
group by customer_group
order by avg_revenue desc;

-- 10. Product retention/repurchase proxy rate
select product_name, buying_customers, order_count, repurchase_proxy_rate
from analytics.mart_product_performance
order by repurchase_proxy_rate desc
limit 20;

-- 11. Voucher assignment to customer groups
select customer_group, recommended_voucher_strategy, customer_count, avg_revenue, avg_transaction_count
from analytics.mart_voucher_recommendations
order by avg_revenue desc;

-- 12. Products with highest return rates
select product_name, category_name, order_count, returned_quantity, return_rate
from analytics.mart_product_performance
where order_count >= 10
order by return_rate desc, returned_quantity desc
limit 20;

-- 13. Product turnover speed proxy
select product_name, category_name, quantity_sold, order_count, revenue
from analytics.mart_product_performance
order by quantity_sold desc
limit 20;

-- 14. Total loss from discounts, shipping subsidies, vouchers, and margin impact
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

-- 15. Peak order hours
select hour_of_day, daypart, order_count, revenue
from analytics.mart_hourly_orders
order by order_count desc;

-- 16. New customers vs returning customers
select
    case when is_new_customer_order then 'New customer order' else 'Returning customer order' end as customer_order_type,
    count(distinct order_id) as order_count,
    sum(total_payment) as revenue
from analytics.fct_order_item
group by 1;

-- 17. Average delivery duration from checkout until delivery
select avg(delivery_duration_minutes) as avg_delivery_duration_minutes
from analytics.fct_order_item
where delivery_duration_minutes is not null;

-- 18. Cancellation rate and status stage where cancellation happens most frequently
select
    cancellation_stage,
    count(distinct case when is_cancelled then order_id end) as cancelled_orders,
    count(distinct order_id) as total_orders,
    count(distinct case when is_cancelled then order_id end)::numeric / nullif(count(distinct order_id), 0) as cancellation_rate
from analytics.fct_order_item
group by cancellation_stage
order by cancelled_orders desc;

-- 19. Product categories with high profit but low sales
with subcategory_metrics as (
    select
        categories.subcategory_name, -- Diubah dari category_name
        sum(facts.profit) as profit,
        sum(facts.quantity) as quantity_sold,
        percent_rank() over (order by sum(facts.profit)) as profit_percentile,
        percent_rank() over (order by sum(facts.quantity)) as quantity_percentile
    from analytics.fct_order_item as facts
    inner join analytics.dim_category as categories
        on facts.category_key = categories.category_key
    group by categories.subcategory_name -- Diubah dari category_name
)
select *
from subcategory_metrics
where profit_percentile >= 0.50 and quantity_percentile <= 0.50
order by profit desc;

-- 20. Cancellation rate for each product
select product_name, order_count, cancellation_rate
from analytics.mart_product_performance
where order_count >= 10
order by cancellation_rate desc
limit 20;

-- 21. High revenue but infrequent customers
select customer_nk, full_name, city_name, transaction_count, revenue, customer_group
from analytics.mart_customer_segments
where customer_group = 'High Revenue Low Frequency'
order by revenue desc;

-- 22. Payment methods with highest transaction value
select payment_method_name, transaction_value, transaction_count, avg_item_value
from analytics.mart_payment_method_performance
order by transaction_value desc;

-- 23 PEAK_SEASON_DATES 
WITH holiday_dates AS (
    SELECT CAST(val AS DATE) AS holiday_date
    FROM (VALUES 
        ('2022-01-01'), ('2022-02-01'), ('2022-03-03'), ('2022-05-02'), ('2022-05-16'), ('2022-07-10'), ('2022-12-25'),
        ('2023-01-01'), ('2023-01-22'), ('2023-03-22'), ('2023-04-22'), ('2023-06-04'), ('2023-06-29'), ('2023-12-25'),
        ('2024-01-01'), ('2024-02-10'), ('2024-03-11'), ('2024-04-10'), ('2024-05-23'), ('2024-06-17'), ('2024-12-25'),
        ('2025-01-01'), ('2025-01-29'), ('2025-03-29'), ('2025-03-31'), ('2025-05-12'), ('2025-06-06'), ('2025-12-25')
    ) AS t(val)
),
transaction_seasons AS (
    SELECT 
        facts.subtotal AS gross_revenue, -- Nilai penjualan kotor sebelum diskon/voucer
        facts.voucher_amount,
        facts.shipping_subsidy,
        CASE 
            WHEN EXISTS (
                SELECT 1 
                FROM holiday_dates h
                -- Memeriksa apakah tanggal transaksi masuk dalam jendela H-10 s.d H+10 hari raya
                WHERE d.date_day BETWEEN h.holiday_date - INTERVAL '10 days' AND h.holiday_date + INTERVAL '10 days'
            ) THEN 'Peak Season'
            ELSE 'Normal Season'
        END AS season_type
    FROM analytics.fct_order_item AS facts
    INNER JOIN analytics.dim_date AS d 
        ON facts.order_date_key = d.date_key
)
SELECT
    season_type AS "Tipe Musim",
    SUM(gross_revenue) AS "Total Pendapatan Kotor (IDR)",
    SUM(voucher_amount) AS "Total Biaya Voucer (IDR)",
    SUM(shipping_subsidy) AS "Total Subsidi Ongkir (IDR)",
    
    -- Menghitung Rasio Perbandingan (%)
    ROUND((SUM(voucher_amount)::NUMERIC / NULLIF(SUM(gross_revenue), 0)) * 100, 2) AS "Rasio Voucer (%)",
    ROUND((SUM(shipping_subsidy)::NUMERIC / NULLIF(SUM(gross_revenue), 0)) * 100, 2) AS "Rasio Subsidi Ongkir (%)",
    ROUND(((SUM(voucher_amount) + SUM(shipping_subsidy))::NUMERIC / NULLIF(SUM(gross_revenue), 0)) * 100, 2) AS "Total Burn Rate Promo (%)"
FROM transaction_seasons
GROUP BY season_type;

--24 top 3 bulan dengan revenue tertinggi di setiap tahunnya
-- 1. Hitung total revenue untuk setiap kombinasi Tahun dan Bulan
WITH monthly_revenue_aggregates AS (
    SELECT
        EXTRACT(YEAR FROM d.date_day) AS year_num,
        EXTRACT(MONTH FROM d.date_day) AS month_num,
        TO_CHAR(d.date_day, 'Month') AS month_name,
        SUM(facts.subtotal) AS total_revenue
    FROM analytics.fct_order_item AS facts
    INNER JOIN analytics.dim_date AS d
        ON facts.order_date_key = d.date_key
    GROUP BY 1, 2, 3
),
ranked_months_cte AS (
    SELECT
        year_num,
        month_name,
        total_revenue,
        ROW_NUMBER() OVER (
            PARTITION BY year_num 
            ORDER BY total_revenue DESC
        ) AS rank_position
    FROM monthly_revenue_aggregates
)
SELECT
    year_num AS "Tahun",
    rank_position AS "Peringkat",
    TRIM(month_name) AS "Bulan",
    total_revenue AS "Total Revenue (IDR)"
FROM ranked_months_cte
WHERE rank_position <= 3
ORDER BY year_num ASC, rank_position ASC;

--25 Number of shipping services per quarter
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

--Segmen pelanggan mana yang memiliki transaksi tertinggi?
SELECT 
    c.loyalty_tier AS "Segmen Pelanggan",
    COUNT(DISTINCT facts.order_id) AS "Total Transaksi (Jumlah Order)",
    SUM(facts.total_payment) AS "Total Nilai Transaksi (IDR)"
FROM analytics.fct_order_item AS facts
INNER JOIN analytics.dim_customer AS c 
    ON facts.customer_key = c.customer_key
GROUP BY 1
ORDER BY 2 DESC;

--Berapa margin keuntungan rata-rata per kategori produk?
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