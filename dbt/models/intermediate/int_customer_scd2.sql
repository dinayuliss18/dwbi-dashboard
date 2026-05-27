with ordered_events as (
    select
        customer_profile_event_id,
        customer_id,
        full_name,
        email,
        gender,
        birth_date,
        city_id,
        loyalty_tier,
        marketing_opt_in,
        effective_at as valid_from,
        lead(effective_at) over (
            partition by customer_id
            order by effective_at, customer_profile_event_id
        ) as next_valid_from
    from {{ ref('stg_customer_profile_events') }}
)

select
    {{ generate_surrogate_key(['customer_id', 'valid_from']) }} as customer_key,
    customer_id as customer_nk,
    full_name,
    email,
    gender,
    birth_date,
    city_id,
    loyalty_tier,
    marketing_opt_in,
    valid_from,
    coalesce(next_valid_from, '9999-12-31'::timestamp) as valid_to,
    next_valid_from is null as is_current
from ordered_events
