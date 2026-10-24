-- Q10a: All runs, by type and status
select
    case
        when end_date - start_date = 1 then 'hourly'
        else 'backfill'
    end                                                       as run_type,
    status,
    count(*)                                                  as runs,
    sum(rows_inserted)                                        as rows_inserted,
    sum(rows_updated)                                         as rows_updated,
    round(avg(extract(epoch from finished_at - started_at)), 1) as avg_seconds
from public.ingest_runs
group by run_type, status
order by run_type, status;

-- Q10b: Hourly runs: first run, last run, success rate
select
    min(started_at)                                            as first_run,
    max(started_at)                                            as last_run,
    count(*)                                                   as hourly_runs,
    count(*) filter (where status = 'success')                 as successes,
    round(100.0 * count(*) filter (where status = 'success')
          / count(*), 1)                                       as success_pct
from public.ingest_runs
where end_date - start_date = 1;

-- Q10c: Any run that did not succeed
select run_id, started_at, status, error_message
from public.ingest_runs
where status <> 'success'
order by started_at desc;