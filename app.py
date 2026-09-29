"""
Amazon India Business Dashboard
Run with:  streamlit run app.py
"""
from __future__ import annotations

from datetime import date

import streamlit as st

from utils.data_processing import DATA_PATH, apply_filters, load_data
from utils.report import build_excel_report, build_html_report
from utils.ui import inject_css

st.set_page_config(
    page_title="Amazon India Dashboard",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Data (cached: cleaned once per session / file change)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading and cleaning sales data…")
def get_clean_data(path: str, _mtime: float):
    return load_data(path)


try:
    full_df, quality = get_clean_data(str(DATA_PATH), DATA_PATH.stat().st_mtime)
except FileNotFoundError:
    st.error(f"Dataset not found. Place **Amazon Sales Data India.xlsx** in `{DATA_PATH.parent}`.")
    st.stop()
except ValueError as e:
    st.error(str(e))
    st.stop()


# ---------------------------------------------------------------------------
# Session defaults
# ---------------------------------------------------------------------------
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

MIN_D, MAX_D = full_df["Order_Date"].min().date(), full_df["Order_Date"].max().date()
ALL_CATS = sorted(full_df["Category"].unique())
ALL_STATES = sorted(full_df["Ship_State"].unique())
ALL_PAY = sorted(full_df["Payment_Method"].unique())
ALL_FUL = sorted(full_df["Fulfillment"].unique())
ALL_STATUS = [s for s in ["Delivered", "Shipped", "Returned", "Cancelled"]
              if s in set(full_df["Order_Status"])]


def reset_filters():
    st.session_state.f_dates = (MIN_D, MAX_D)
    for key in ("f_cats", "f_states", "f_pay", "f_ful", "f_status"):
        st.session_state[key] = []


if "f_dates" not in st.session_state:
    reset_filters()


# ---------------------------------------------------------------------------
# Sidebar: brand, theme toggle, global filters
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """<div class="brand"><div class="brand-mark">a</div>
           <div><div class="brand-name">Amazon India</div>
           <div class="brand-sub">Business Performance Dashboard</div></div></div>""",
        unsafe_allow_html=True,
    )
    st.toggle("🌙 Dark mode", key="dark_mode")
    st.session_state.theme_mode = "dark" if st.session_state.dark_mode else "light"

inject_css()

pages = [
    st.Page("pages/1_Executive_Dashboard.py", title="Executive Dashboard", icon="📊", default=True),
    st.Page("pages/2_Category_Product.py", title="Category & Product", icon="🛍️"),
    st.Page("pages/3_Order_Status.py", title="Order Status & Revenue Loss", icon="📦"),
    st.Page("pages/4_Payment_Fulfillment.py", title="Payment & Fulfillment", icon="💳"),
    st.Page("pages/5_Geographic.py", title="Geographic Performance", icon="🗺️"),
]
nav = st.navigation(pages, position="sidebar")

with st.sidebar:
    st.divider()
    st.markdown("### 🔎 Global filters")
    dates = st.date_input("Date range", min_value=MIN_D, max_value=MAX_D,
                          key="f_dates", format="DD/MM/YYYY")
    cats = st.multiselect("Category", ALL_CATS, key="f_cats", placeholder="All categories")
    states = st.multiselect("State", ALL_STATES, key="f_states", placeholder="All states")
    with st.expander("More filters"):
        pay = st.multiselect("Payment method", ALL_PAY, key="f_pay", placeholder="All")
        ful = st.multiselect("Fulfillment", ALL_FUL, key="f_ful", placeholder="All")
        status = st.multiselect("Order status", ALL_STATUS, key="f_status", placeholder="All")
    st.button("↺ Reset filters", on_click=reset_filters)

# A date range picker returns a single date while the user is mid-selection.
if isinstance(dates, (tuple, list)) and len(dates) == 2:
    start, end = dates
elif isinstance(dates, (tuple, list)) and len(dates) == 1:
    start, end = dates[0], MAX_D
elif isinstance(dates, date):
    start, end = dates, MAX_D
else:
    start, end = MIN_D, MAX_D

filtered = apply_filters(
    full_df,
    start=start,
    end=f"{end} 23:59:59",
    categories=cats, states=states, payments=pay, fulfillments=ful, statuses=status,
)

filters_text = (
    f"{start:%d %b %Y} to {end:%d %b %Y}; "
    f"Category: {', '.join(cats) if cats else 'All'}; "
    f"State: {', '.join(states) if states else 'All'}"
    + (f"; Payment: {', '.join(pay)}" if pay else "")
    + (f"; Fulfillment: {', '.join(ful)}" if ful else "")
    + (f"; Status: {', '.join(status)}" if status else "")
)

st.session_state.full_df = full_df
st.session_state.filtered_df = filtered
st.session_state.filters_text = filters_text
st.session_state.data_quality = quality


# ---------------------------------------------------------------------------
# Sidebar: downloads
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def make_reports(df, text):
    return build_html_report(df, text), build_excel_report(df, text)


with st.sidebar:
    st.divider()
    st.markdown("### ⬇️ Downloads")
    st.caption(f"{len(filtered):,} of {len(full_df):,} orders match the filters")
    st.download_button(
        "Filtered data (CSV)",
        data=filtered.drop(columns=["Is_Lost"]).to_csv(index=False).encode("utf-8-sig"),
        file_name="amazon_india_filtered_data.csv",
        mime="text/csv",
        disabled=filtered.empty,
    )
    if not filtered.empty:
        html_report, xlsx_report = make_reports(filtered, filters_text)
        st.download_button("Dashboard report (HTML)", data=html_report,
                           file_name="amazon_india_dashboard_report.html", mime="text/html")
        st.download_button(
            "Dashboard report (Excel)", data=xlsx_report,
            file_name="amazon_india_dashboard_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.divider()
    with st.expander("🧹 Data quality"):
        st.markdown(
            f"- Rows loaded: **{quality['rows_in']:,}**\n"
            f"- Missing values found: **{quality['missing_before']}**\n"
            f"- Duplicates removed: **{quality['duplicates_removed']}**\n"
            f"- Invalid rows removed: **{quality['invalid_removed']}**\n"
            f"- Rows analysed: **{quality['rows_out']:,}**\n"
            f"- Data covers **{MIN_D:%d %b %Y} – {MAX_D:%d %b %Y}**"
        )

if filtered.empty:
    st.warning("No orders match the selected filters. Widen the date range or clear some filters.")
    st.stop()

nav.run()
