select
    order_id,
    status_event_id,
    status,
    status_ts,
    row_number() over (partition by order_id order by status_ts, status_event_id) as status_sequence,
    lead(status_ts) over (partition by order_id order by status_ts, status_event_id) as next_status_ts,
    max(case when status = 'cancelled' then status_ts end) over (partition by order_id) as cancelled_ts,
    max(case when status = 'returned' then status_ts end) over (partition by order_id) as returned_ts
from {{ ref('stg_order_status_events') }}
