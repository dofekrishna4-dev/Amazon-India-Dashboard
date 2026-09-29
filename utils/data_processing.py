"""
Data loading, cleaning, feature engineering, KPI calculation and
automatic business insights for the Amazon India Dashboard.

Everything in this module is plain pandas, so it can be imported and
tested without Streamlit running.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "Amazon Sales Data India.xlsx"

EXPECTED_COLUMNS = [
    "Order_ID", "Order_Date", "Category", "Product", "Quantity",
    "Unit_Price_INR", "Discount_Pct", "Total_Sales_INR", "Profit_INR",
    "Payment_Method", "Fulfillment", "Order_Status", "Ship_State",
]
NUMERIC_COLUMNS = ["Quantity", "Unit_Price_INR", "Discount_Pct", "Total_Sales_INR", "Profit_INR"]
TEXT_COLUMNS = ["Order_ID", "Category", "Product", "Payment_Method",
                "Fulfillment", "Order_Status", "Ship_State"]

STATUS_ORDER = ["Delivered", "Shipped", "Returned", "Cancelled"]
MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Approximate geographic centres used for the India bubble map.
STATE_COORDS = {
    "Andhra Pradesh": (15.91, 79.74), "Bihar": (25.10, 85.31),
    "Delhi": (28.70, 77.10), "Gujarat": (22.26, 71.19),
    "Haryana": (29.06, 76.09), "Karnataka": (15.32, 75.71),
    "Kerala": (10.85, 76.27), "Madhya Pradesh": (22.97, 78.66),
    "Maharashtra": (19.75, 75.71), "Odisha": (20.95, 85.10),
    "Punjab": (31.15, 75.34), "Rajasthan": (27.02, 74.22),
    "Tamil Nadu": (11.13, 78.66), "Telangana": (18.11, 79.02),
    "Uttar Pradesh": (26.85, 80.95), "West Bengal": (22.99, 87.85),
    "Assam": (26.20, 92.94), "Jharkhand": (23.61, 85.28),
    "Chhattisgarh": (21.28, 81.87), "Goa": (15.30, 74.12),
}
STATE_REGION = {
    "Delhi": "North", "Uttar Pradesh": "North", "Rajasthan": "North",
    "Punjab": "North", "Haryana": "North",
    "Maharashtra": "West", "Gujarat": "West", "Goa": "West",
    "Karnataka": "South", "Kerala": "South", "Tamil Nadu": "South",
    "Telangana": "South", "Andhra Pradesh": "South",
    "West Bengal": "East", "Bihar": "East", "Odisha": "East",
    "Jharkhand": "East", "Assam": "East",
    "Madhya Pradesh": "Central", "Chhattisgarh": "Central",
}


# --------------------------------------------------------------------------
# Formatting helpers
# --------------------------------------------------------------------------
def fmt_inr(value: float, decimals: int = 2) -> str:
    """Format a rupee amount the Indian way: ₹ Cr / ₹ L / ₹ K."""
    if value is None or pd.isna(value):
        return "₹0"
    sign = "-" if value < 0 else ""
    v = abs(float(value))
    if v >= 1e7:
        return f"{sign}₹{v / 1e7:.{decimals}f} Cr"
    if v >= 1e5:
        return f"{sign}₹{v / 1e5:.{decimals}f} L"
    if v >= 1e3:
        return f"{sign}₹{v / 1e3:.1f} K"
    return f"{sign}₹{v:,.0f}"


def fmt_num(value: float) -> str:
    """Indian digit grouping, e.g. 12,34,567."""
    n = int(round(float(value)))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-" if n < 0 else "") + s


def fmt_pct(value: float, decimals: int = 1) -> str:
    if value is None or pd.isna(value):
        return "0.0%"
    return f"{value:.{decimals}f}%"


# --------------------------------------------------------------------------
# Loading & cleaning
# --------------------------------------------------------------------------
def load_raw_data(path: str | Path = DATA_PATH) -> pd.DataFrame:
    """Read the first sheet of the Excel workbook with openpyxl."""
    return pd.read_excel(path, engine="openpyxl")


def clean_data(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Clean the raw sales data and add engineered features.

    Returns the cleaned frame and a small report of what was changed, which
    the app shows under "Data quality".
    """
    df = raw.copy()
    report = {"rows_in": len(df)}

    # --- column validation -------------------------------------------------
    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")
    df = df[EXPECTED_COLUMNS]

    # --- text normalisation ------------------------------------------------
    for col in TEXT_COLUMNS:
        df[col] = df[col].astype("string").str.strip()
        df[col] = df[col].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})

    # --- type conversion ---------------------------------------------------
    df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce")
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Discount may be stored as a fraction (0.15) or a percentage (15).
    # This dataset stores fractions; normalise to 0-1 either way.
    if df["Discount_Pct"].max(skipna=True) > 1:
        df["Discount_Pct"] = df["Discount_Pct"] / 100

    # --- missing values ----------------------------------------------------
    report["missing_before"] = int(df.isna().sum().sum())
    # Rows without an ID or a date cannot be analysed.
    df = df.dropna(subset=["Order_ID", "Order_Date"])
    for col in ["Category", "Product", "Payment_Method", "Fulfillment", "Ship_State"]:
        df[col] = df[col].fillna("Unknown")
    df["Order_Status"] = df["Order_Status"].fillna("Delivered")
    df["Discount_Pct"] = df["Discount_Pct"].fillna(0)
    df["Quantity"] = df["Quantity"].fillna(df["Quantity"].median())
    df["Unit_Price_INR"] = df["Unit_Price_INR"].fillna(
        df.groupby("Product")["Unit_Price_INR"].transform("median"))
    # Recompute sales from its components where it is missing.
    recomputed = df["Quantity"] * df["Unit_Price_INR"] * (1 - df["Discount_Pct"])
    df["Total_Sales_INR"] = df["Total_Sales_INR"].fillna(recomputed.round(2))
    df["Profit_INR"] = df["Profit_INR"].fillna(0)
    df = df.dropna(subset=["Total_Sales_INR"])
    report["missing_after"] = int(df.isna().sum().sum())

    # --- duplicates ----------------------------------------------------------
    before = len(df)
    df = df.drop_duplicates()
    df = df.drop_duplicates(subset="Order_ID", keep="first")
    report["duplicates_removed"] = before - len(df)

    # --- validation --------------------------------------------------------
    before = len(df)
    df = df[(df["Quantity"] > 0) & (df["Unit_Price_INR"] > 0) & (df["Total_Sales_INR"] >= 0)]
    report["invalid_removed"] = before - len(df)

    df["Quantity"] = df["Quantity"].astype(int)
    for col in ["Category", "Product", "Payment_Method", "Fulfillment",
                "Order_Status", "Ship_State"]:
        df[col] = df[col].astype(str)
    df["Order_ID"] = df["Order_ID"].astype(str)

    # --- feature engineering -----------------------------------------------
    df["Year"] = df["Order_Date"].dt.year.astype(int)
    df["Month"] = df["Order_Date"].dt.month.astype(int)
    df["Month_Name"] = df["Order_Date"].dt.strftime("%b")
    df["Quarter"] = "Q" + df["Order_Date"].dt.quarter.astype(str)
    df["Year_Quarter"] = df["Year"].astype(str) + "-" + df["Quarter"]
    df["Year_Month"] = df["Order_Date"].dt.to_period("M").dt.to_timestamp()
    df["Profit_Margin"] = np.where(
        df["Total_Sales_INR"] > 0, df["Profit_INR"] / df["Total_Sales_INR"] * 100, 0.0
    ).round(2)
    df["Discount_Amount_INR"] = (
        df["Quantity"] * df["Unit_Price_INR"] * df["Discount_Pct"]).round(2)
    df["Is_Lost"] = df["Order_Status"].isin(["Returned", "Cancelled"])
    df["Region"] = df["Ship_State"].map(STATE_REGION).fillna("Other")

    df = df.sort_values("Order_Date").reset_index(drop=True)
    report["rows_out"] = len(df)
    return df, report


def load_data(path: str | Path = DATA_PATH) -> tuple[pd.DataFrame, dict]:
    return clean_data(load_raw_data(path))


# --------------------------------------------------------------------------
# Filtering
# --------------------------------------------------------------------------
def apply_filters(df: pd.DataFrame, start=None, end=None, categories=None,
                  states=None, payments=None, fulfillments=None,
                  statuses=None) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    if start is not None:
        mask &= df["Order_Date"] >= pd.Timestamp(start)
    if end is not None:
        mask &= df["Order_Date"] <= pd.Timestamp(end)
    for col, values in [("Category", categories), ("Ship_State", states),
                        ("Payment_Method", payments), ("Fulfillment", fulfillments),
                        ("Order_Status", statuses)]:
        if values:
            mask &= df[col].isin(values)
    return df[mask]


# --------------------------------------------------------------------------
# KPIs
# --------------------------------------------------------------------------
def compute_kpis(df: pd.DataFrame) -> dict:
    sales = float(df["Total_Sales_INR"].sum())
    profit = float(df["Profit_INR"].sum())
    orders = int(df["Order_ID"].nunique())
    units = int(df["Quantity"].sum())
    counts = df["Order_Status"].value_counts()
    lost = df[df["Is_Lost"]]
    return {
        "total_sales": sales,
        "total_profit": profit,
        "total_orders": orders,
        "total_units": units,
        "aov": sales / orders if orders else 0.0,
        "profit_margin": profit / sales * 100 if sales else 0.0,
        "delivered": int(counts.get("Delivered", 0)),
        "shipped": int(counts.get("Shipped", 0)),
        "returned": int(counts.get("Returned", 0)),
        "cancelled": int(counts.get("Cancelled", 0)),
        "return_rate": counts.get("Returned", 0) / orders * 100 if orders else 0.0,
        "cancel_rate": counts.get("Cancelled", 0) / orders * 100 if orders else 0.0,
        "lost_returns": float(df.loc[df["Order_Status"] == "Returned", "Total_Sales_INR"].sum()),
        "lost_cancel": float(df.loc[df["Order_Status"] == "Cancelled", "Total_Sales_INR"].sum()),
        "lost_total": float(lost["Total_Sales_INR"].sum()),
        "net_sales": sales - float(lost["Total_Sales_INR"].sum()),
        "avg_discount": float(df["Discount_Pct"].mean() * 100) if len(df) else 0.0,
    }


def period_delta(df: pd.DataFrame, full_df: pd.DataFrame, metric: str = "Total_Sales_INR"):
    """
    Compare the last complete month in the selection with the month before.
    Returns (pct_change, label) or (None, None).
    """
    monthly = df.groupby("Year_Month")[metric].sum().sort_index()
    if len(monthly) < 2:
        return None, None
    last, prev = monthly.iloc[-1], monthly.iloc[-2]
    if prev == 0:
        return None, None
    return (last - prev) / prev * 100, f"{monthly.index[-1]:%b %Y} vs {monthly.index[-2]:%b %Y}"


# --------------------------------------------------------------------------
# Aggregations reused by pages and reports
# --------------------------------------------------------------------------
def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    m = (df.groupby("Year_Month")
           .agg(Sales=("Total_Sales_INR", "sum"), Profit=("Profit_INR", "sum"),
                Orders=("Order_ID", "nunique"), Units=("Quantity", "sum"))
           .reset_index())
    m["Margin_%"] = np.where(m["Sales"] > 0, m["Profit"] / m["Sales"] * 100, 0).round(2)
    return m


def group_summary(df: pd.DataFrame, by: str) -> pd.DataFrame:
    g = (df.groupby(by)
           .agg(Sales=("Total_Sales_INR", "sum"), Profit=("Profit_INR", "sum"),
                Orders=("Order_ID", "nunique"), Units=("Quantity", "sum"),
                Returned=("Order_Status", lambda s: (s == "Returned").sum()),
                Cancelled=("Order_Status", lambda s: (s == "Cancelled").sum()))
           .reset_index())
    g["Margin_%"] = np.where(g["Sales"] > 0, g["Profit"] / g["Sales"] * 100, 0).round(2)
    g["Return_Rate_%"] = np.where(g["Orders"] > 0, g["Returned"] / g["Orders"] * 100, 0).round(2)
    g["Cancel_Rate_%"] = np.where(g["Orders"] > 0, g["Cancelled"] / g["Orders"] * 100, 0).round(2)
    total = g["Sales"].sum()
    g["Sales_Share_%"] = (g["Sales"] / total * 100).round(2) if total else 0
    g["AOV"] = np.where(g["Orders"] > 0, g["Sales"] / g["Orders"], 0).round(2)
    return g.sort_values("Sales", ascending=False).reset_index(drop=True)


def lost_revenue_by(df: pd.DataFrame, by: str) -> pd.DataFrame:
    lost = df[df["Is_Lost"]]
    t = (lost.pivot_table(index=by, columns="Order_Status", values="Total_Sales_INR",
                          aggfunc="sum", fill_value=0)
             .reindex(columns=["Returned", "Cancelled"], fill_value=0)
             .reset_index())
    t.columns.name = None
    t["Total_Lost"] = t["Returned"] + t["Cancelled"]
    return t.sort_values("Total_Lost", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------
# Automatic insights (plain-English, for a non-technical reader)
# --------------------------------------------------------------------------
def _top(g: pd.DataFrame, col: str, key: str):
    row = g.sort_values(col, ascending=False).iloc[0]
    return row[key], row


def executive_insights(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []
    k = compute_kpis(df)
    out = []
    m = monthly_summary(df)
    best = m.loc[m["Sales"].idxmax()]
    worst = m.loc[m["Sales"].idxmin()]
    out.append(f"**Best month:** {best['Year_Month']:%B %Y} with sales of "
               f"{fmt_inr(best['Sales'])}; the weakest was {worst['Year_Month']:%B %Y} "
               f"({fmt_inr(worst['Sales'])}).")

    years = df.groupby("Year").agg(Sales=("Total_Sales_INR", "sum"),
                                   Months=("Month", "nunique"))
    if len(years) >= 2:
        years["Per_Month"] = years["Sales"] / years["Months"]
        y1, y0 = years.index[-1], years.index[-2]
        chg = (years.loc[y1, "Per_Month"] - years.loc[y0, "Per_Month"]) / years.loc[y0, "Per_Month"] * 100
        trend = "up" if chg >= 0 else "down"
        note = ""
        if years.loc[y1, "Months"] < 12:
            note = f" ({y1} has {years.loc[y1, 'Months']} months of data so far, so this compares average monthly sales)"
        out.append(f"**Year-on-year:** average monthly sales in {y1} are {trend} "
                   f"{abs(chg):.1f}% versus {y0}{note}.")

    out.append(f"**Profitability:** the business keeps {fmt_pct(k['profit_margin'])} of every "
               f"rupee of sales as profit; the average order is worth {fmt_inr(k['aov'])}.")
    cat = group_summary(df, "Category")
    name, row = _top(cat, "Sales", "Category")
    out.append(f"**Best performing category:** {name}, contributing "
               f"{fmt_pct(row['Sales_Share_%'])} of sales.")
    out.append(f"**Revenue at risk:** returns and cancellations account for "
               f"{fmt_inr(k['lost_total'])} ({fmt_pct(k['lost_total'] / k['total_sales'] * 100)} of sales).")
    return out


def category_insights(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []
    cat = group_summary(df, "Category")
    prod = group_summary(df, "Product")
    out = []
    n, r = _top(cat, "Sales", "Category")
    out.append(f"**Best performing category:** {n} leads with {fmt_inr(r['Sales'])} in sales.")
    n, r = _top(cat, "Profit", "Category")
    out.append(f"**Most profitable category:** {n} with {fmt_inr(r['Profit'])} profit.")
    n, r = _top(cat, "Margin_%", "Category")
    lo = cat.sort_values("Margin_%").iloc[0]
    out.append(f"**Margins:** {n} has the highest margin ({fmt_pct(r['Margin_%'])}); "
               f"{lo['Category']} has the lowest ({fmt_pct(lo['Margin_%'])}).")
    n, r = _top(cat, "Units", "Category")
    out.append(f"**Volume leader:** {n} sold the most units ({fmt_num(r['Units'])}).")
    n, r = _top(prod, "Profit", "Product")
    out.append(f"**Most profitable product:** {n} ({fmt_inr(r['Profit'])} profit, "
               f"{fmt_pct(r['Margin_%'])} margin).")
    top10_share = prod.head(10)["Sales"].sum() / prod["Sales"].sum() * 100
    out.append(f"**Concentration:** the top 10 products generate {fmt_pct(top10_share)} "
               f"of total sales.")
    if len(prod) > 3:
        weak = prod.sort_values("Profit").iloc[0]
        out.append(f"**Needs attention:** {weak['Product']} earns the least profit "
                   f"({fmt_inr(weak['Profit'])}).")
    return out


def status_insights(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []
    k = compute_kpis(df)
    cat = group_summary(df, "Category")
    out = [
        f"**Fulfilment success:** {fmt_pct((k['delivered'] + k['shipped']) / k['total_orders'] * 100)} "
        f"of orders were delivered or are on the way.",
        f"**Returns:** {fmt_num(k['returned'])} orders ({fmt_pct(k['return_rate'])}) came back, "
        f"costing {fmt_inr(k['lost_returns'])} in sales.",
        f"**Cancellations:** {fmt_num(k['cancelled'])} orders ({fmt_pct(k['cancel_rate'])}) were "
        f"cancelled, costing {fmt_inr(k['lost_cancel'])} in sales.",
    ]
    avg_rr = k["return_rate"]
    risky = cat[cat["Return_Rate_%"] > avg_rr].sort_values("Return_Rate_%", ascending=False)
    if not risky.empty:
        items = ", ".join(f"{r['Category']} ({r['Return_Rate_%']:.1f}%)"
                          for _, r in risky.iterrows())
        out.append(f"**Return risk categories:** {items} — above the overall "
                   f"return rate of {avg_rr:.1f}%.")
    n, r = _top(cat, "Cancel_Rate_%", "Category")
    out.append(f"**Highest cancellation rate:** {n} ({fmt_pct(r['Cancel_Rate_%'])}).")
    lost = lost_revenue_by(df, "Category")
    if not lost.empty:
        top = lost.iloc[0]
        out.append(f"**Biggest revenue leak:** {top['Category']} lost "
                   f"{fmt_inr(top['Total_Lost'])} to returns and cancellations.")
    return out


def payment_insights(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []
    pay = group_summary(df, "Payment_Method")
    ful = group_summary(df, "Fulfillment")
    out = []
    used = pay.sort_values("Orders", ascending=False).iloc[0]
    out.append(f"**Most used payment method:** {used['Payment_Method']} — "
               f"{fmt_pct(used['Orders'] / pay['Orders'].sum() * 100)} of all orders.")
    n, r = _top(pay, "Profit", "Payment_Method")
    out.append(f"**Most profitable payment method:** {n} ({fmt_inr(r['Profit'])}).")
    n, r = _top(pay, "AOV", "Payment_Method")
    out.append(f"**Biggest baskets:** customers paying by {n} spend the most per order "
               f"({fmt_inr(r['AOV'])}).")
    n, r = _top(pay, "Return_Rate_%", "Payment_Method")
    out.append(f"**Payment return risk:** {n} has the highest return rate "
               f"({fmt_pct(r['Return_Rate_%'])}).")
    n, r = _top(ful, "Sales", "Fulfillment")
    out.append(f"**Leading fulfilment channel:** {n} handles {fmt_pct(r['Sales_Share_%'])} of sales.")
    n, r = _top(ful, "Margin_%", "Fulfillment")
    out.append(f"**Best-margin channel:** {n} ({fmt_pct(r['Margin_%'])} margin).")
    return out


def geo_insights(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []
    st_ = group_summary(df, "Ship_State")
    out = []
    n, r = _top(st_, "Sales", "Ship_State")
    out.append(f"**Highest revenue state:** {n} with {fmt_inr(r['Sales'])} "
               f"({fmt_pct(r['Sales_Share_%'])} of sales).")
    n, r = _top(st_, "Profit", "Ship_State")
    out.append(f"**Most profitable state:** {n} ({fmt_inr(r['Profit'])}).")
    n, r = _top(st_, "Orders", "Ship_State")
    out.append(f"**Most orders:** {n} placed {fmt_num(r['Orders'])} orders.")
    low = st_.sort_values("Sales").iloc[0]
    out.append(f"**Smallest market:** {low['Ship_State']} ({fmt_inr(low['Sales'])}) — a "
               f"growth opportunity.")
    top3 = st_.head(3)["Sales"].sum() / st_["Sales"].sum() * 100
    out.append(f"**Concentration:** the top 3 states bring in {fmt_pct(top3)} of sales.")
    reg = group_summary(df, "Region")
    n, r = _top(reg, "Sales", "Region")
    out.append(f"**Strongest region:** {n} India ({fmt_pct(r['Sales_Share_%'])} of sales).")
    n, r = _top(st_, "Return_Rate_%", "Ship_State")
    out.append(f"**Watch list:** {n} has the highest return rate ({fmt_pct(r['Return_Rate_%'])}).")
    return out


def all_insights(df: pd.DataFrame) -> dict[str, list[str]]:
    return {
        "Executive Summary": executive_insights(df),
        "Category & Product Performance": category_insights(df),
        "Order Status & Revenue Loss": status_insights(df),
        "Payment & Fulfillment": payment_insights(df),
        "Geographic Performance": geo_insights(df),
    }
