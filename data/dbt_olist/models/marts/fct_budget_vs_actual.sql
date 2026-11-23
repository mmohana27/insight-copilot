with actual as (
    select
        f.purchase_year  as fiscal_year,
        f.purchase_month as fiscal_month,
        p.category,
        sum(f.price)     as actual_revenue
    from {{ ref('fct_sales') }} f
    join {{ ref('dim_products') }} p on p.product_id = f.product_id
    group by 1, 2, 3
)

select
    cast(b.fiscal_year as varchar) || '-'
        || lpad(cast(b.fiscal_month as varchar), 2, '0') || '-' || b.category as budget_key,
    b.fiscal_year,
    b.fiscal_month,
    b.category,
    coalesce(a.actual_revenue, 0)                                   as actual_revenue,
    b.budget_revenue,
    coalesce(a.actual_revenue, 0) - b.budget_revenue                as variance,
    round(100.0 * (coalesce(a.actual_revenue, 0) - b.budget_revenue)
          / nullif(b.budget_revenue, 0), 2)                         as variance_pct
from {{ ref('stg_budget') }} b
left join actual a
    on  a.fiscal_year  = b.fiscal_year
    and a.fiscal_month = b.fiscal_month
    and a.category     = b.category