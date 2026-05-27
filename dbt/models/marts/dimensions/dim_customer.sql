select
    customers.customer_key,
    customers.customer_nk,
    cities.city_key,
    customers.full_name,
    customers.email,
    customers.gender,
    customers.birth_date,
    date_part('year', age(current_date, customers.birth_date))::integer as age_years,
    customers.loyalty_tier,
    customers.marketing_opt_in,
    customers.valid_from,
    customers.valid_to,
    customers.is_current
from {{ ref('int_customer_scd2') }} as customers
inner join {{ ref('dim_city') }} as cities
    on customers.city_id = cities.city_nk
