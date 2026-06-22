select
    session_id,
    user_id,
    session_duration_minutes,
    to_char(session_start, 'YYYYMMDD')::integer as date_id,
    session_start,
    device_type
from {{ ref('stg_sessions') }}
