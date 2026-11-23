"""Generate 10 synthetic enterprise documents (PDF) for the RAG system.

All documents are SYNTHETIC and written for this portfolio project.
Facts (column names, campaign names, dates) match the warehouse tables.
"""
from html import escape
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "rag" / "docs"

DOCS = [
    {
        "file": "kpi_definitions.pdf",
        "title": "KPI Definitions Handbook",
        "owner": "Finance and Analytics",
        "sections": [
            ("Revenue", [
                "Gross revenue is the sum of item price (column price in marts.fct_sales). It excludes freight, which is reported separately as freight_value.",
                "Delivered revenue is gross revenue restricted to order_status = 'delivered'. When a question says completed or realised revenue, use delivered revenue.",
                "When no qualifier is given, report gross revenue and state that it includes canceled and unavailable orders.",
                "Total item value is price plus freight_value.",
            ]),
            ("Orders and basket size", [
                "Orders is the count of distinct order_id, not the count of rows, because one order can contain several items.",
                "Average order value (AOV) is gross revenue divided by orders.",
            ]),
            ("Delivery performance", [
                "Delivery days is the number of calendar days between purchase date and delivery date. It is only defined for delivered orders.",
                "A delivery is late when it arrives after the estimated delivery date (column is_late). Late delivery rate is late items divided by delivered items.",
            ]),
            ("Customer satisfaction", [
                "Average review score is the mean of review_score on a 1 to 5 scale. Orders with several reviews are averaged first so that each order counts once.",
            ]),
            ("Profitability", [
                "Operating costs are the sum of six cost types: cost_of_goods, marketing, logistics_overhead, platform_tech, customer_support and payroll.",
                "Operating profit is revenue minus operating costs. Operating margin percent is operating profit divided by revenue, multiplied by 100.",
            ]),
            ("Budget", [
                "Variance is actual revenue minus budget revenue. Variance percent is variance divided by budget revenue, multiplied by 100. A negative value means the category missed budget.",
            ]),
            ("Time conventions", [
                "Months are calendar months based on the purchase date. Data coverage is reliable from January 2017 to August 2018. Months outside this window have very few orders and should not be used for trend conclusions.",
            ]),
        ],
    },
    {
        "file": "data_dictionary.pdf",
        "title": "Data Dictionary: Analytics Warehouse",
        "owner": "Data Platform Team",
        "sections": [
            ("Overview", [
                "Business-ready tables live in the marts schema. Each table is tested for unique keys and valid relationships. Analysts and the AI assistant should query marts, never the raw schema.",
            ]),
            ("marts.fct_sales", [
                "One row per item sold. Key: sales_item_id.",
                "Columns: sales_item_id, order_id, item_number, customer_id, product_id, seller_id, order_status, purchased_at, purchase_date, purchase_year, purchase_month, price, freight_value, total_item_value, delivered_at, estimated_delivery_at, delivery_days, is_late, review_score.",
            ]),
            ("Dimension tables", [
                "marts.dim_customers: customer_id, customer_unique_id, city, state. customer_id is created per order. customer_unique_id identifies the real person across orders, so use it to count unique customers.",
                "marts.dim_products: product_id, category (English name), category_name_pt, weight_g, length_cm, height_cm, width_cm, photo_count. Products without a category show 'unknown'.",
                "marts.dim_sellers: seller_id, city, state.",
            ]),
            ("Finance tables", [
                "marts.fct_budget_vs_actual: budget_key, fiscal_year, fiscal_month, category, actual_revenue, budget_revenue, variance, variance_pct.",
                "marts.fct_monthly_pnl: fiscal_year, fiscal_month, year_month, orders, revenue, freight, operating_costs, operating_profit, operating_margin_pct. One row per month.",
            ]),
            ("Marketing table", [
                "staging.stg_marketing_campaigns: campaign_id, campaign_name, channel, start_date, end_date, target_state, spend. target_state is a two-letter state code or ALL.",
            ]),
            ("Joining tables", [
                "Join fct_sales to dim_customers on customer_id, to dim_products on product_id, and to dim_sellers on seller_id. States are two-letter codes such as SP, RJ and MG.",
                "Finance figures for operating costs and budgets are synthetic planning data, not audited accounts.",
            ]),
        ],
    },
    {
        "file": "refund_return_policy.pdf",
        "title": "Refund and Return Policy",
        "owner": "Customer Operations",
        "sections": [
            ("Return window", [
                "Customers may return an item within 7 calendar days of delivery for any reason (change of mind). The item must be unused and in its original packaging.",
                "For damaged, defective or wrong items, the return window is 30 calendar days from delivery.",
            ]),
            ("How refunds are paid", [
                "Refunds are issued to the original payment method within 10 business days of the returned item being received.",
                "Credit card and debit card refunds go back to the card. Boleto refunds are paid by bank transfer, and the customer must provide bank details. Voucher payments are refunded as store credit.",
            ]),
            ("Shipping costs", [
                "Return shipping is free when the return is caused by a seller error or a damaged product. For a change of mind, the customer pays return shipping.",
                "The original freight is refunded only when the seller is at fault.",
            ]),
            ("Orders that were never delivered", [
                "If an order is canceled or marked unavailable before delivery, the customer receives a full refund including freight. No return is needed.",
                "If an order is more than 20 days past its estimated delivery date, the customer may cancel and receive a full refund.",
            ]),
            ("Reporting impact", [
                "Refunds are not netted out of fct_sales. Canceled and unavailable orders stay in the table with their order_status, so analysts must filter them when they need net revenue.",
            ]),
        ],
    },
    {
        "file": "delivery_sla_policy.pdf",
        "title": "Delivery Service Level Policy",
        "owner": "Logistics",
        "sections": [
            ("Promise to the customer", [
                "At checkout, every order receives an estimated delivery date. An order is late if it arrives after that date.",
            ]),
            ("Targets", [
                "On-time delivery target: at least 90 percent of delivered items arrive on or before the estimated date.",
                "Average delivery time target: 12 calendar days or fewer from purchase to delivery.",
                "Seller handoff target: sellers must give the order to the carrier within 3 business days of payment approval.",
            ]),
            ("Escalation rules", [
                "If the late delivery rate for any state exceeds 15 percent in a month, Logistics opens a carrier review for that state.",
                "If a seller misses the handoff target on more than 10 percent of their orders in a month, the seller receives a written warning.",
            ]),
            ("Reporting", [
                "Delivery performance is reported using delivery_days and is_late from marts.fct_sales. Only delivered orders are included in delivery metrics.",
            ]),
        ],
    },
    {
        "file": "finance_close_calendar.pdf",
        "title": "Monthly Finance Close Calendar",
        "owner": "Finance",
        "sections": [
            ("Monthly close timeline", [
                "Business day 1: revenue cut-off. Orders are counted by purchase date in the closing month.",
                "Business day 3: operating cost accruals are booked for all six cost types.",
                "Business day 5: budget variance review. Finance analysts review fct_budget_vs_actual.",
                "Business day 7: the monthly profit and loss (fct_monthly_pnl) is published to leadership.",
            ]),
            ("Variance review rules", [
                "Any product category with an absolute variance percent above 15 percent must be explained in writing, whether over or under budget.",
                "Categories with budget revenue below 1,000 in a month are excluded from review because small numbers create misleading percentages.",
            ]),
            ("Quarter end", [
                "Quarters end on March 31, June 30, September 30 and December 31. Quarter-end close adds a forecast refresh on business day 8.",
            ]),
            ("Cost types", [
                "cost_of_goods is the purchase cost of products sold. marketing is campaign spend. logistics_overhead covers warehousing and carrier management. platform_tech covers hosting and software. customer_support covers the service team. payroll covers salaries.",
            ]),
            ("Margin guardrail", [
                "If operating margin percent falls below 5 percent in any month, Finance must notify the leadership team on the day the P and L is published.",
            ]),
        ],
    },
    {
        "file": "marketing_campaign_playbook.pdf",
        "title": "Marketing Campaign Playbook and Calendar",
        "owner": "Marketing",
        "sections": [
            ("Channels", [
                "We run five channels: email, social, search, influencer and tv. Email is the lowest cost per order. TV has the widest reach and is used only for the largest seasonal moments.",
            ]),
            ("Attribution rule", [
                "A campaign is credited with sales from its start date until 7 days after its end date. When campaigns overlap, spend and credit are reviewed manually.",
            ]),
            ("Campaign calendar 2017", [
                "C001 Summer Sale 2017: email, January 16 to January 31, all states, spend 18,000.",
                "C002 Carnival Fashion Push: social, February 20 to March 5, RJ only, spend 12,500.",
                "C003 Mothers Day 2017: search, May 1 to May 14, all states, spend 30,000.",
                "C004 Winter Home Refresh: influencer, June 15 to July 10, SP only, spend 22,000.",
                "C005 Fathers Day 2017: email, August 1 to August 13, all states, spend 16,000.",
                "C006 Childrens Day 2017: social, October 1 to October 12, all states, spend 14,000.",
                "C007 Black Friday 2017: search, November 20 to November 27, all states, spend 85,000.",
                "C008 Christmas 2017: tv, December 1 to December 20, all states, spend 60,000.",
            ]),
            ("Campaign calendar 2018", [
                "C009 New Year Electronics: email, January 8 to January 31, SP only, spend 20,000.",
                "C010 Carnival 2018: social, February 5 to February 14, RJ only, spend 15,000.",
                "C011 Mothers Day 2018: search, April 28 to May 13, all states, spend 38,000.",
                "C012 World Cup 2018: tv, June 10 to July 14, all states, spend 70,000.",
                "C013 Back to Basics Brand: influencer, July 20 to August 20, MG only, spend 24,000.",
            ]),
            ("Evaluating a campaign", [
                "Compare revenue during the attribution window with the same number of days before the campaign. Report uplift as a percentage, and divide the extra revenue by spend to get return on spend.",
            ]),
        ],
    },
    {
        "file": "seasonality_and_events_brief.pdf",
        "title": "Seasonality and Key Events Brief",
        "owner": "Commercial Strategy",
        "sections": [
            ("Why seasonality matters", [
                "Online retail demand is driven by gift occasions and shopping events. Comparing a month with the previous month can mislead. Compare with the same month a year earlier when the data allows it.",
            ]),
            ("Key events", [
                "Black Friday (late November) is the single biggest shopping event. November 2017 was the highest-revenue month in the warehouse, with about 7,451 orders.",
                "Christmas drives December demand, but delivery delays in December often increase the late delivery rate.",
                "Mothers Day (second Sunday of May) lifts April and May. In 2018, April and May were among the strongest months.",
                "Fathers Day (second Sunday of August), Childrens Day (October 12) and Carnival (February) create smaller peaks.",
                "The 2018 World Cup (mid June to mid July) shifted demand toward sports, electronics and televisions.",
            ]),
            ("Data coverage warning", [
                "Order volume before January 2017 and after August 2018 is very small. Do not interpret growth rates that start or end in those months.",
            ]),
            ("Interpreting a spike", [
                "Check three things before explaining a spike: campaigns running in the period, the shopping event calendar, and whether one category or state drove most of the change.",
            ]),
        ],
    },
    {
        "file": "customer_service_and_reviews_policy.pdf",
        "title": "Customer Service and Reviews Policy",
        "owner": "Customer Operations",
        "sections": [
            ("Review scores", [
                "Customers rate an order from 1 (very unhappy) to 5 (very happy). Scores of 4 and 5 are positive, 3 is neutral, and 1 and 2 are negative.",
                "Target: an average review score of 4.0 or higher for every month.",
            ]),
            ("Handling negative reviews", [
                "Every review of 1 or 2 stars must receive a reply within 48 hours. The reply offers help and, where the policy allows, a refund or replacement.",
                "Three or more negative reviews on the same seller within a month trigger a seller quality review.",
            ]),
            ("Common causes of low scores", [
                "Late delivery is the most common cause of a low score. Orders flagged is_late in fct_sales usually have lower review scores than on-time orders.",
                "Other frequent causes are damaged products, wrong items and items that differ from the description.",
            ]),
            ("Support hours", [
                "The service team answers from 8am to 8pm, Monday to Saturday. Messages sent outside these hours are answered the next working day.",
            ]),
        ],
    },
    {
        "file": "data_governance_and_privacy.pdf",
        "title": "Data Governance and AI Usage Policy",
        "owner": "Data Governance Office",
        "sections": [
            ("Approved data sources", [
                "The AI assistant may only read tables in the marts schema. It must never read the raw or staging schemas, except staging.stg_marketing_campaigns, which is approved for campaign questions.",
            ]),
            ("Query rules", [
                "All AI-generated SQL must be read-only: SELECT statements only. INSERT, UPDATE, DELETE, DROP, ALTER and similar statements are forbidden.",
                "Every query must have a row limit of 1,000 rows or fewer. Queries are checked before they run.",
            ]),
            ("Personal data", [
                "customer_unique_id is a pseudonymous identifier. The warehouse holds no names, emails, phone numbers or street addresses. If personal data is ever found in a table, the AI must mask it in answers.",
                "Answers must not list individual customers. Results should be aggregated by state, category, month or similar groups.",
            ]),
            ("Audit and accountability", [
                "Every question, generated SQL statement, answer and user identifier is written to the audit schema. Audit records are kept for at least 12 months.",
                "Every answer must cite the tables or documents it used, so a reviewer can check it.",
            ]),
            ("Synthetic data notice", [
                "Budget, operating cost and marketing campaign data in this environment are synthetic and built for demonstration. They must not be presented as audited financial results.",
            ]),
        ],
    },
    {
        "file": "product_category_guide.pdf",
        "title": "Product Category Guide",
        "owner": "Merchandising",
        "sections": [
            ("Category naming", [
                "The category column in marts.dim_products uses English names with underscores, for example health_beauty, bed_bath_table, sports_leisure, computers_accessories and furniture_decor. The original Portuguese name is kept in category_name_pt.",
                "Products with no category assigned show 'unknown'. Treat these as uncategorised, not as a real category.",
            ]),
            ("Category groups for reporting", [
                "Home: bed_bath_table, furniture_decor, housewares. Technology: computers_accessories, telephony, electronics. Lifestyle: health_beauty, sports_leisure, watches_gifts, toys.",
                "Leadership reports usually show the ten largest categories by revenue and group the rest as Other.",
            ]),
            ("Budgeting by category", [
                "Budgets are set per month and per category. Small categories have very volatile variance percentages, so review them together with the absolute amounts.",
            ]),
            ("Shipping characteristics", [
                "Heavy and bulky categories such as furniture have higher freight as a share of price and more late deliveries. Use weight_g and the product dimensions in dim_products to explain freight differences.",
            ]),
        ],
    },
]


def build_pdf(doc: dict) -> Path:
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    body.leading = 15
    path = OUT / doc["file"]
    pdf = SimpleDocTemplate(
        str(path), pagesize=A4, title=doc["title"], author=doc["owner"],
        leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
    )
    story = [
        Paragraph(escape(doc["title"]), styles["Title"]),
        Paragraph(
            escape(f"Owner: {doc['owner']}  |  Version 1.0  |  Synthetic document for a portfolio project"),
            styles["Italic"],
        ),
        Spacer(1, 0.5 * cm),
    ]
    for heading, paragraphs in doc["sections"]:
        story.append(Paragraph(escape(heading), styles["Heading2"]))
        for text in paragraphs:
            story.append(Paragraph(escape(text), body))
            story.append(Spacer(1, 0.15 * cm))
    pdf.build(story)
    return path


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for doc in DOCS:
        build_pdf(doc)

    print(f"Created {len(DOCS)} PDFs in {OUT}\n")
    for p in sorted(OUT.glob("*.pdf")):
        reader = PdfReader(p)
        text = "".join(page.extract_text() or "" for page in reader.pages)
        print(f"{p.name:<45} {len(reader.pages)} page(s) {len(text):>6,} chars")


if __name__ == "__main__":
    main()