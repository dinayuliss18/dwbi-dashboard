select
    {{ generate_surrogate_key(['products.product_id']) }} as product_key,
    products.product_id as product_nk,
    categories.category_key,
    products.sku,
    products.product_name,
    products.standard_price,
    products.estimated_unit_cost,
    products.is_active,
    products.created_at
from {{ ref('stg_products') }} as products
inner join {{ ref('dim_category') }} as categories
    on products.category_id = categories.category_nk
