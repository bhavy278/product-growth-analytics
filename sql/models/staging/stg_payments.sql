select
    payment_id,
    user_id,
    amount::numeric as amount,
    payment_date::date as payment_date
from {{ source('staging_sources', 'raw_payments') }}
