select
    cast(fiscal_year as integer)           as fiscal_year,
    cast(fiscal_month as integer)          as fiscal_month,
    category,
    cast(budget_revenue as numeric(14, 2)) as budget_revenue
from {{ source('raw_finance', 'budget') }}