select count(*) as city_count
from {{ ref('dim_city') }}
having count(*) <> 34
