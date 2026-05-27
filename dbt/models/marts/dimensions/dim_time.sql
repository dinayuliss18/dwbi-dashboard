with time_spine as (
    select generate_series(0, 1439) as minute_of_day
)

select
    minute_of_day as time_key,
    make_time((minute_of_day / 60)::integer, (minute_of_day % 60)::integer, 0) as time_value,
    (minute_of_day / 60)::integer as hour_of_day,
    (minute_of_day % 60)::integer as minute_of_hour,
    case
        when (minute_of_day / 60)::integer between 0 and 5 then 'Late Night'
        when (minute_of_day / 60)::integer between 6 and 10 then 'Morning'
        when (minute_of_day / 60)::integer between 11 and 14 then 'Lunch'
        when (minute_of_day / 60)::integer between 15 and 17 then 'Afternoon'
        when (minute_of_day / 60)::integer between 18 and 21 then 'Evening'
        else 'Night'
    end as daypart
from time_spine
