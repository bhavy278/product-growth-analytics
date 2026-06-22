select
    user_id,
    signup_date::date as signup_date,
    country,
    acquisition_channel,
    plan_type
from {{ source('staging_sources', 'raw_users') }}
