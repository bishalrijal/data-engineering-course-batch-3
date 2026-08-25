-- duration_minutes is only populated for completed trips; when present it
-- must be non-negative (completed_at can't be before requested_at)
select *
from {{ ref('fact_trips') }}
where duration_minutes is not null
  and duration_minutes < 0
