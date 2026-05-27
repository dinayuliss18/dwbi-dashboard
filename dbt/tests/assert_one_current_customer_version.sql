select
    customer_nk,
    count(*) as current_row_count
from {{ ref('dim_customer') }}
where is_current
group by customer_nk
having count(*) <> 1
