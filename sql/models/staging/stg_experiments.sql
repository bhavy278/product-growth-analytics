select
    experiment_id,
    variant,
    user_id,
    assigned_date::timestamp as assigned_date
from {{ source('staging_sources', 'raw_experiments') }}
