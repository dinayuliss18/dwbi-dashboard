select
    city_id,
    city_name,
    province,
    region,
    country,
    loaded_at
from {{ source('raw', 'cities') }}
