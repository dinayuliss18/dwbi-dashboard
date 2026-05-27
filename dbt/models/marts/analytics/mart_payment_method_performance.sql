select
    payment.payment_method_name,
    payment.payment_group,
    count(distinct facts.order_id) as transaction_count,
    sum(facts.total_payment) as transaction_value,
    avg(facts.total_payment) as avg_item_value,
    sum(facts.voucher_amount) as voucher_amount,
    sum(facts.discount_amount + facts.voucher_amount + facts.shipping_subsidy) as total_promo_loss
from {{ ref('fct_order_item') }} as facts
inner join {{ ref('dim_payment_method') }} as payment
    on facts.payment_method_key = payment.payment_method_key
group by payment.payment_method_name, payment.payment_group
