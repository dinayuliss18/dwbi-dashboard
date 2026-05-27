select count(*) as order_item_count
from {{ ref('fct_order_item') }}
having count(*) < 10000
