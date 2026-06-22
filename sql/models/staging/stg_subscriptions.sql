select
    subscription_id,
    user_id,
    plan,
    start_date::date as start_date,
    case 
        when end_date = '' then null 
        else end_date::date 
    end as end_date,
    status
from {{ source('staging_sources', 'raw_subscriptions') }}
