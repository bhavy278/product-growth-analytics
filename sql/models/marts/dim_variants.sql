select
    user_id,
    experiment_id,
    variant,
    assigned_date
from {{ ref('stg_experiments') }}
