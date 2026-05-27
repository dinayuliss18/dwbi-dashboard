select
    category_id,
    category_name,
    subcategory_name,
    department,
    loaded_at
from {{ source('raw', 'categories') }}
