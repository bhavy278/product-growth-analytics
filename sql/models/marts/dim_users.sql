select
    user_id,
    signup_date,
    country,
    acquisition_channel as channel,
    plan_type as current_plan
from {{ ref('stg_users') }}
