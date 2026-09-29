<p align="center"><img src="assets/favicon.svg" width="72" alt="Dashboard icon"></p>

# Amazon India Business Dashboard
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://amazon-india-dashboard-edyavpmmhoh8xbqt8eaezt.streamlit.app)

🔗 **Live demo:** https://amazon-india-dashboard-edyavpmmhoh8xbqt8eaezt.streamlit.app — no installation needed.

An interactive management dashboard, built with Streamlit and Plotly, for 10,000 Amazon India orders (Jan 2024 – Aug 2026).
It answers the four business questions in the Sapphire IQ brief for a non-technical manager:

1. **How is the business performing overall?** (Executive Dashboard)
2. **Which products and categories are driving the business?** (Category & Product)
3. **How many orders are completed, and how many are lost?** (Order Status & Revenue Loss)
4. **Which payment methods, fulfilment channels and states generate business?** (Payment & Fulfillment, Geographic)

---

## Quick start

```bash
# 1. (optional) create a virtual environment
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate

# 2. install dependencies
pip install -r requirements.txt

# 3. run the app
streamlit run app.py
```

The dashboard opens at <http://localhost:8501>. You need Python 3.9 or newer.

> The dataset must be at `data/Amazon Sales Data India.xlsx`. To analyse a different
> file with the same 13 columns, replace that file and the app reloads it automatically.

---

## Project structure

```
amazon_dashboard/
├── app.py                        # Entry point: data loading, sidebar navigation, global filters, downloads
├── requirements.txt
├── README.md
├── .streamlit/config.toml        # Amazon-themed base theme
├── assets/
│   ├── style.css                 # Custom UI (KPI cards, header, sidebar, light/dark tokens)
│   └── favicon.svg
├── data/
│   └── Amazon Sales Data India.xlsx
├── utils/
│   ├── data_processing.py        # Cleaning, feature engineering, KPIs, aggregations, auto-insights
│   ├── report.py                 # HTML + Excel (OpenPyXL) report generators
│   └── ui.py                     # Theme, KPI cards, chart styling helpers
└── pages/
    ├── 1_Executive_Dashboard.py
    ├── 2_Category_Product.py
    ├── 3_Order_Status.py
    ├── 4_Payment_Fulfillment.py
    └── 5_Geographic.py
```

---

## Data cleaning & feature engineering (`utils/data_processing.py`)

| Step | What happens |
|---|---|
| Column validation | Checks that all 13 required columns exist and trims header whitespace |
| Date conversion | `Order_Date` text → datetime; rows with invalid dates are dropped |
| Type validation | Numeric columns coerced to numbers; `Discount_Pct` normalised to a 0–1 fraction |
| Missing values | Text → `"Unknown"`; discount → 0; quantity → median; price → product median; sales recomputed as `Qty × Price × (1 − Discount)` |
| Duplicates | Exact duplicate rows and repeated `Order_ID`s removed |
| Validation | Rows with non-positive quantity/price or negative sales removed |
| New features | `Year`, `Month`, `Month_Name`, `Quarter`, `Year_Quarter`, `Year_Month`, `Profit_Margin` (%), `Discount_Amount_INR`, `Is_Lost`, `Region` |

A **Data quality** panel in the sidebar reports what the cleaning changed. The supplied file is already clean: 0 missing values and 0 duplicates.

---

## Pages

| Page | KPIs | Charts |
|---|---|---|
| **Executive Dashboard** | Total Sales, Total Profit, Total Orders, Units Sold, Avg Order Value, Profit Margin % | Monthly Sales Trend, Monthly Profit Trend (with 3-month averages), Sales vs Profit by Quarter, Sales by Year |
| **Category & Product** | Top category, most profitable product, top-10 share | Category-wise Sales / Profit / Units, Top 10 Products by Sales, Top 10 by Profit, Product Contribution % treemap |
| **Order Status & Revenue Loss** | Delivered, Shipped, Returned, Cancelled, Return Rate %, Cancellation Rate %, Revenue Lost, Net Sales | Status distribution donut, monthly returns/cancellations, category-wise returns and cancellations, revenue lost to returns, revenue lost to cancellations, monthly revenue lost |
| **Payment & Fulfillment** | Most used payment, digital-payment share, top channel, best channel margin | Sales / Profit by Payment Method, Payment Method Share %, payment mix by category, Sales / Profit by Fulfillment, return & cancel rate by channel |
| **Geographic** | States served, top state by sales and by profit, top region | India bubble map, sales by region, region→state sunburst, state-wise Sales / Profit / Orders, Top 10 States by Sales / Profit, state × category heatmap |

Each page ends with an automatically generated **Business insights** box, for example: best performing category, most profitable product, highest revenue state, most used payment method, and return-risk categories. The text is recalculated whenever a filter changes.

---

## Features

- **Sidebar navigation** between the 5 pages (`st.navigation`)
- **Global filters** for date range, category and state, plus payment method, fulfilment and order status under *More filters*. They apply to every page and can be cleared with *Reset filters*.
- **Dynamic KPIs**: all cards, charts and insights update when a filter changes
- **Downloads**:
  - Filtered data as CSV
  - Dashboard report as HTML: KPIs, insights, interactive charts and summary tables. It is printable to PDF from a browser.
  - Dashboard report as Excel: a formatted, multi-sheet workbook built with OpenPyXL, with native Excel charts and the filtered raw data
- **Dark / Light mode** toggle in the sidebar
- **Responsive layout**: KPI grid reflows on small screens, and charts resize with the window
- **Amazon-themed UI**: squid-ink navy with orange accents, and a colour-blind-safe chart palette where each category keeps the same colour on every page

---

## KPI definitions

| KPI | Formula |
|---|---|
| Total Sales | Σ `Total_Sales_INR` (gross booked sales, including returned and cancelled orders) |
| Total Profit | Σ `Profit_INR` |
| Total Orders | Count of unique `Order_ID` |
| Units Sold | Σ `Quantity` |
| Average Order Value | Total Sales ÷ Total Orders |
| Profit Margin % | Total Profit ÷ Total Sales × 100 |
| Return Rate % | Returned orders ÷ Total Orders × 100 |
| Cancellation Rate % | Cancelled orders ÷ Total Orders × 100 |
| Revenue Lost | Σ sales of Returned (or Cancelled) orders |
| Net Sales | Total Sales − Revenue Lost |

In this dataset, returned and cancelled orders carry **₹0 profit**, so they lower the profit margin.

---

## Headline results (full dataset)

- Total sales **₹15.58 Cr**, profit **₹3.32 Cr**, margin **21.3%**, 10,000 orders, AOV **₹15.6 K**
- **Electronics & Mobiles** is 79% of sales. The top 10 products make up ~91% of sales.
- Return rate **4.9%**, cancellation rate **5.0%**. Together they lose **₹1.56 Cr** (10% of gross sales).
- **UPI** is used for ~50% of orders. **Amazon (FBA)** handles 69% of sales.
- **Maharashtra** is the top state (19% of sales), and **South India** is the top region (40%).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` inside the active environment |
| "Dataset not found" | Put the Excel file at `data/Amazon Sales Data India.xlsx` (exact name) |
| `st.navigation` / `st.Page` errors | Upgrade Streamlit: `pip install -U streamlit` (needs 1.40 or newer) |
| Map background missing | The India map downloads its base outline from the Plotly CDN, so the browser needs internet access |

## Tech stack

Python · Streamlit · Pandas · NumPy · Plotly · OpenPyXL
