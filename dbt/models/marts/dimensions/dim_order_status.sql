select
    {{ generate_surrogate_key(['status']) }} as order_status_key,
    status as order_status,
    case
        when status in ('placed', 'paid', 'packed', 'shipped') then 'Open'
        when status = 'delivered' then 'Completed'
        when status in ('cancelled', 'returned') then 'Exception'
        else 'Unknown'
    end as status_group,
    case status
        when 'placed' then 1
        when 'paid' then 2
        when 'packed' then 3
        when 'shipped' then 4
        when 'delivered' then 5
        when 'cancelled' then 6
        when 'returned' then 7
        else 99
    end as status_sort_order
from (
    select distinct order_status as status from {{ ref('stg_orders') }}
    union
    select distinct status from {{ ref('stg_order_status_events') }}
) as statuses
