select
    {{ generate_surrogate_key(['city_id']) }} as city_key,
    city_id as city_nk,
    city_name,
    province,
    region,
    country
from {{ ref('stg_cities') }}
