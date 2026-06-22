with date_series as (
    select generate_series(
        '2025-06-01'::date,
        '2026-07-01'::date,
        '1 day'::interval
    )::date as date_day
)
select
    to_char(date_day, 'YYYYMMDD')::integer as date_id,
    date_day as date,
    extract(week from date_day)::integer as week,
    extract(month from date_day)::integer as month,
    extract(quarter from date_day)::integer as quarter,
    extract(year from date_day)::integer as year
from date_series
