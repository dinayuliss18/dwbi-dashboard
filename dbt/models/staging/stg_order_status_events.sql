select
    status_event_id,
    order_id,
    status,
    status_ts,
    loaded_at
from {{ source('raw', 'order_status_events') }}
