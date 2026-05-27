select
    order_id,
    item_number,
    count(*) as row_count
from {{ ref('fct_order_item') }}
group by order_id, item_number
having count(*) > 1
