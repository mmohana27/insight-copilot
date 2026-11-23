select
    campaign_id,
    campaign_name,
    channel,
    cast(start_date as date)   as start_date,
    cast(end_date as date)     as end_date,
    target_state,
    cast(spend as numeric(12, 2)) as spend
from {{ source('raw_finance', 'marketing_campaigns') }}