select
    payment_id,
    user_id,
    amount,
    to_char(payment_date, 'YYYYMMDD')::integer as date_id,
    payment_date
from {{ ref('stg_payments') }}
