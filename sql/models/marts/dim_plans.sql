select distinct
    plan as plan_name,
    case
        when plan = 'Free' then 1
        when plan = 'Pro' then 2
        when plan = 'Enterprise' then 3
        else 0
    end as plan_id
from {{ ref('stg_subscriptions') }}
