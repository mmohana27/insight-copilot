with items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

reviews as (
    -- some orders have more than one review, so average them to one row per order
    select
        order_id,
        round(avg(review_score), 2) as review_score
    from {{ ref('stg_order_reviews') }}
    group by order_id
)

select
    cast(i.order_id as varchar) || '-' || cast(i.item_number as varchar) as sales_item_id,
    i.order_id,
    i.item_number,
    o.customer_id,
    i.product_id,
    i.seller_id,
    o.order_status,
    o.purchased_at,
    cast(o.purchased_at as date)                as purchase_date,
    cast(extract(year from o.purchased_at) as integer)  as purchase_year,
    cast(extract(month from o.purchased_at) as integer) as purchase_month,
    i.price,
    i.freight_value,
    i.price + i.freight_value                   as total_item_value,
    o.delivered_at,
    o.estimated_delivery_at,
    case
        when o.delivered_at is not null
        then cast(o.delivered_at as date) - cast(o.purchased_at as date)
    end                                         as delivery_days,
    case
        when o.delivered_at is null then null
        when o.delivered_at > o.estimated_delivery_at then true
        else false
    end                                         as is_late,
    r.review_score
from items i
join orders o on o.order_id = i.order_id
left join reviews r on r.order_id = i.order_id