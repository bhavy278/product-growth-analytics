select
    event_id,
    user_id,
    event_type,
    to_char(event_time, 'YYYYMMDD')::integer as date_id,
    event_time
from {{ ref('stg_events') }}
