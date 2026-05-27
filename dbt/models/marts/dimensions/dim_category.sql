select
    {{ generate_surrogate_key(['category_id']) }} as category_key,
    category_id as category_nk,
    category_name,
    subcategory_name,
    department
from {{ ref('stg_categories') }}
