select
    p.product_id,
    coalesce(t.category_name_english, p.category_name, 'unknown') as category,
    p.category_name                                               as category_name_pt,
    p.weight_g,
    p.length_cm,
    p.height_cm,
    p.width_cm,
    p.photo_count
from {{ ref('stg_products') }} p
left join {{ ref('stg_product_category_translation') }} t
    on t.category_name = p.category_name