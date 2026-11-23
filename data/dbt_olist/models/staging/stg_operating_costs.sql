select
    cast(fiscal_year as integer)   as fiscal_year,
    cast(fiscal_month as integer)  as fiscal_month,
    cost_type,
    cast(amount as numeric(14, 2)) as amount
from {{ source('raw_finance', 'operating_costs') }}