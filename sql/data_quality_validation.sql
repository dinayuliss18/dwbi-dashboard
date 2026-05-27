-- Validate fact grain
select order_id, item_number, count(*)
from analytics.fct_order_item
group by order_id, item_number
having count(*) > 1;

-- Validate minimum 10,000 order item transactions
select count(*) as order_item_count
from analytics.fct_order_item;

-- Validate 34 cities
select count(*) as city_count
from analytics.dim_city;

-- Validate SCD2 has one current row per customer
select customer_nk, count(*)
from analytics.dim_customer
where is_current
group by customer_nk
having count(*) <> 1;

-- Validate SCD2 versions do not overlap
select a.customer_nk, a.customer_key, b.customer_key
from analytics.dim_customer a
join analytics.dim_customer b
  on a.customer_nk = b.customer_nk
 and a.customer_key <> b.customer_key
 and a.valid_from < b.valid_to
 and b.valid_from < a.valid_to;

-- Validate required fact measures are not null
select count(*) as bad_rows
from analytics.fct_order_item
where quantity is null
   or unit_price is null
   or subtotal is null
   or discount_amount is null
   or shipping_subsidy is null
   or voucher_amount is null
   or total_payment is null
   or estimated_cost is null
   or profit is null
   or is_returned is null
   or is_cancelled is null;

-- Validate amount formula
select order_item_id
from analytics.fct_order_item
where abs(total_payment - (subtotal - discount_amount - voucher_amount)) > 0.01;

-- Validate profit formula
select order_item_id
from analytics.fct_order_item
where abs(profit - (total_payment - estimated_cost - shipping_subsidy)) > 0.01;

-- Validate relationship coverage
select count(*) as missing_product_dim
from analytics.fct_order_item f
left join analytics.dim_product d
  on f.product_key = d.product_key
where d.product_key is null;
