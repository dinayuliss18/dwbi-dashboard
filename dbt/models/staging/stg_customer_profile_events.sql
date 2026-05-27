select
    customer_profile_event_id,
    customer_id,
    full_name,
    lower(email) as email,
    gender,
    birth_date,
    city_id,
    loyalty_tier,
    marketing_opt_in,
    effective_at,
    operation,
    loaded_at
from {{ source('raw', 'customer_profile_events') }}
