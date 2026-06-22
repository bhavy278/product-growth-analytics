select
    session_id,
    user_id,
    session_start::timestamp as session_start,
    session_end::timestamp as session_end,
    device_type,
    extract(epoch from (session_end::timestamp - session_start::timestamp)) / 60.0 as session_duration_minutes
from {{ source('staging_sources', 'raw_sessions') }}
