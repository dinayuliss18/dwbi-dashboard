# Suggested BI Dashboards and KPIs

Use Metabase or Power BI connected to PostgreSQL schema `analytics`.

## Executive Revenue Dashboard

| KPI | Source |
| --- | --- |
| Monthly revenue | `mart_monthly_revenue.net_revenue` |
| Gross revenue | `mart_monthly_revenue.gross_revenue` |
| Profit | `mart_monthly_revenue.profit` |
| Profit margin | `mart_monthly_revenue.profit_margin` |
| Promo loss | `discount_amount + shipping_subsidy + voucher_amount` |
| Order count | `mart_monthly_revenue.order_count` |

## City and Customer Dashboard

| KPI | Source |
| --- | --- |
| Revenue by city | `mart_city_performance` |
| Transaction count by city | `mart_city_performance` |
| Customer groups | `mart_customer_segments.customer_group` |
| High revenue low frequency customers | `mart_customer_segments` |
| New vs returning customers | `fct_order_item.is_new_customer_order` |

## Product Dashboard

| KPI | Source |
| --- | --- |
| Top 10 products by revenue | `mart_product_performance` |
| Top 10 products by quantity | `mart_product_performance` |
| Product return rate | `mart_product_performance.return_rate` |
| Product cancellation rate | `mart_product_performance.cancellation_rate` |
| High profit low sales products | `mart_product_performance` |

## Payment and Voucher Dashboard

| KPI | Source |
| --- | --- |
| Payment method frequency | `mart_payment_method_performance.transaction_count` |
| Payment method value | `mart_payment_method_performance.transaction_value` |
| Voucher loss by payment method | `mart_payment_method_performance.voucher_amount` |
| Voucher recommendation by customer group | `mart_voucher_recommendations` |

## Shipping Operations Dashboard

| KPI | Source |
| --- | --- |
| Shipping service usage | `mart_shipping_performance.order_count` |
| Cancellation by shipping service | `mart_shipping_performance.cancelled_order_count` |
| Fastest shipping service | `mart_shipping_performance.fastest_delivery_minutes` |
| Slowest shipping service | `mart_shipping_performance.slowest_delivery_minutes` |
| Delay rate | `mart_shipping_performance.delay_rate` |
| Average checkout-to-delivery duration | `mart_shipping_performance.avg_delivery_duration_minutes` |

## Operational Behavior Dashboard

| KPI | Source |
| --- | --- |
| Peak order hours | `mart_hourly_orders` |
| Cancellation rate by status stage | `fct_order_item.cancellation_stage` |
| Return rate | `fct_order_item.is_returned` |
| Cancellation rate | `fct_order_item.is_cancelled` |
