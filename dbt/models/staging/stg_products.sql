select
    product_id,
    sku,
    product_name,
    category_id,
    standard_price::bigint as standard_price,
    estimated_unit_cost::bigint as estimated_unit_cost,
    is_active,
    created_at,
    loaded_at
from {{ source('raw', 'products') }}
