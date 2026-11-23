with revenue as (
    select
        purchase_year  as fiscal_year,
        purchase_month as fiscal_month,
        count(distinct order_id) as orders,
        sum(price)               as revenue,
        sum(freight_value)       as freight
    from {{ ref('fct_sales') }}
    group by 1, 2
),

costs as (
    select
        fiscal_year,
        fiscal_month,
        sum(amount) as operating_costs
    from {{ ref('stg_operating_costs') }}
    group by 1, 2
)

select
    r.fiscal_year,
    r.fiscal_month,
    cast(r.fiscal_year as varchar) || '-' || lpad(cast(r.fiscal_month as varchar), 2, '0') as year_month,
    r.orders,
    r.revenue,
    r.freight,
    c.operating_costs,
    r.revenue - c.operating_costs as operating_profit,
    round(100.0 * (r.revenue - c.operating_costs) / nullif(r.revenue, 0), 2) as operating_margin_pct
from revenue r
join costs c
    on  c.fiscal_year  = r.fiscal_year
    and c.fiscal_month = r.fiscal_month