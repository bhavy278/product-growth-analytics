select
    event_id,
    user_id,
    event_time::timestamp as event_time,
    event_type
from {{ source('staging_sources', 'raw_events') }}
