with date_spine as (
    -- Batas akhir diperpanjang hingga 2030 agar aman menampung data incremental tahun 2026+
    select generate_series('2022-01-01'::date, '2040-12-31'::date, interval '1 day')::date as date_day
)

select
    to_char(date_day, 'YYYYMMDD')::integer as date_key,
    date_day,
    extract(year from date_day)::integer as year,
    extract(quarter from date_day)::integer as quarter,
    extract(month from date_day)::integer as month,
    to_char(date_day, 'Month') as month_name,
    extract(day from date_day)::integer as day_of_month,
    extract(isodow from date_day)::integer as day_of_week,
    to_char(date_day, 'Day') as day_name,
    extract(week from date_day)::integer as week_of_year,
    (extract(isodow from date_day) in (6, 7)) as is_weekend
from date_spine