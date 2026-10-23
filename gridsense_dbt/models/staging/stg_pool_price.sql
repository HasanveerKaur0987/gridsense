with source as (

    select * from {{ source('aeso', 'raw_pool_price') }}

),

renamed as (

    select
        begin_datetime_utc                        as hour_start_utc,
        begin_datetime_mpt                        as hour_start_mpt,
        pool_price,
        forecast_pool_price,
        rolling_30day_avg,

        -- helper columns (all based on Alberta time)
        begin_datetime_mpt::date                  as price_date,
        extract(hour from begin_datetime_mpt) + 1 as hour_ending,
        extract(isodow from begin_datetime_mpt)   as day_of_week,   -- Mon=1 ... Sun=7
        extract(month from begin_datetime_mpt)    as month,
        extract(year from begin_datetime_mpt)     as year,
        pool_price is not null                    as is_final,

        loaded_at,
        updated_at
    from source

)

select * from renamed