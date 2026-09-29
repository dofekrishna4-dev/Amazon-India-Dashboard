"""Page 1 — Executive Dashboard: overall sales & profit performance."""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.data_processing import (compute_kpis, executive_insights, fmt_inr, fmt_num,
                                   fmt_pct, monthly_summary, period_delta)
from utils.ui import (get_data, lakh_table, insights_box, kpi_card, kpi_row, page_header, profit_color,
                      sales_color, section, show_chart, show_table, style_fig, theme)

df, full_df = get_data()
k = compute_kpis(df)

page_header("📊 Executive Dashboard",
            "How is the business performing overall? Sales, profit and order volume at a glance.")

# ---------------- KPI cards ----------------
delta, delta_label = period_delta(df, full_df)
delta_txt = ""
if delta is not None:
    arrow = "▲" if delta >= 0 else "▼"
    delta_txt = f"{arrow} {abs(delta):.1f}% · {delta_label}"

kpi_row([
    kpi_card("Total Sales", fmt_inr(k["total_sales"]), delta_txt or "Gross booked sales", "💰"),
    kpi_card("Total Profit", fmt_inr(k["total_profit"]), f"Net sales {fmt_inr(k['net_sales'])}", "📈", "good"),
    kpi_card("Total Orders", fmt_num(k["total_orders"]), f"{fmt_num(k['delivered'])} delivered", "🧾", "info"),
    kpi_card("Units Sold", fmt_num(k["total_units"]),
             f"{k['total_units'] / max(k['total_orders'], 1):.1f} units / order", "📦"),
    kpi_card("Avg Order Value", fmt_inr(k["aov"]), f"Avg discount {k['avg_discount']:.1f}%", "🛒"),
    kpi_card("Profit Margin", fmt_pct(k["profit_margin"]), "Profit ÷ sales", "🎯", "good"),
])

m = monthly_summary(df)
t = theme()

# ---------------- Trends ----------------
c1, c2 = st.columns(2)
with c1:
    fig = px.area(m, x="Year_Month", y="Sales", title="Monthly Sales Trend",
                  labels={"Year_Month": "", "Sales": "Sales (₹)"})
    fig.update_traces(line=dict(color=sales_color(), width=2),
                      fillcolor="rgba(42,120,214,0.12)", mode="lines+markers",
                      marker=dict(size=6),
                      hovertemplate="%{x|%b %Y}<br>Sales ₹%{y:,.0f}<extra></extra>")
    if len(m) >= 3:
        fig.add_trace(go.Scatter(x=m["Year_Month"], y=m["Sales"].rolling(3).mean(),
                                 name="3-month average", mode="lines",
                                 line=dict(color=t["muted"], width=2, dash="dot"),
                                 hovertemplate="3-mo avg ₹%{y:,.0f}<extra></extra>"))
    show_chart(style_fig(fig, inr_max=m["Sales"].max()))
with c2:
    fig = px.area(m, x="Year_Month", y="Profit", title="Monthly Profit Trend",
                  labels={"Year_Month": "", "Profit": "Profit (₹)"})
    fig.update_traces(line=dict(color=profit_color(), width=2),
                      fillcolor="rgba(27,175,122,0.12)", mode="lines+markers",
                      marker=dict(size=6),
                      hovertemplate="%{x|%b %Y}<br>Profit ₹%{y:,.0f}<extra></extra>")
    if len(m) >= 3:
        fig.add_trace(go.Scatter(x=m["Year_Month"], y=m["Profit"].rolling(3).mean(),
                                 name="3-month average", mode="lines",
                                 line=dict(color=t["muted"], width=2, dash="dot"),
                                 hovertemplate="3-mo avg ₹%{y:,.0f}<extra></extra>"))
    show_chart(style_fig(fig, inr_max=m["Profit"].max()))

c3, c4 = st.columns(2)
with c3:
    q = (df.groupby("Year_Quarter")
           .agg(Sales=("Total_Sales_INR", "sum"), Profit=("Profit_INR", "sum"))
           .reset_index())
    ql = q.melt(id_vars="Year_Quarter", var_name="Measure", value_name="INR")
    fig = px.bar(ql, x="Year_Quarter", y="INR", color="Measure", barmode="group",
                 title="Sales vs Profit by Quarter",
                 color_discrete_map={"Sales": sales_color(), "Profit": profit_color()},
                 labels={"Year_Quarter": "", "INR": "Amount", "Measure": ""})
    fig.update_traces(hovertemplate="%{x}<br>%{fullData.name} ₹%{y:,.0f}<extra></extra>",
                      marker_cornerradius=4)
    fig.update_xaxes(tickangle=-45)
    show_chart(style_fig(fig, inr_max=ql["INR"].max()))
with c4:
    y = (df.groupby("Year")
           .agg(Sales=("Total_Sales_INR", "sum"), Profit=("Profit_INR", "sum"),
                Months=("Month", "nunique"))
           .reset_index())
    y["Label"] = y.apply(lambda r: f"{int(r.Year)}" + (f" ({int(r.Months)} mo)" if r.Months < 12 else ""), axis=1)
    y["Text"] = y["Sales"].map(fmt_inr)
    fig = px.bar(y, x="Label", y="Sales", text="Text", title="Sales by Year",
                 labels={"Label": "", "Sales": "Sales (₹)"})
    fig.update_traces(marker_color=sales_color(), textposition="outside", marker_cornerradius=4,
                      hovertemplate="%{x}<br>Sales ₹%{y:,.0f}<extra></extra>", cliponaxis=False)
    show_chart(style_fig(fig, legend=False, inr_max=y["Sales"].max() * 1.15))
    if (y["Months"] < 12).any():
        st.caption("Years marked with a month count are partial years in the data.")

insights_box(executive_insights(df))

with st.expander("📋 Monthly summary table"):
    view = m.copy()
    view["Month"] = view["Year_Month"].dt.strftime("%b %Y")
    view = view[["Month", "Sales", "Profit", "Margin_%", "Orders", "Units"]]
    view, cfg = lakh_table(view, ["Sales", "Profit"])
    cfg["Margin_%"] = st.column_config.NumberColumn("Margin %", format="%.1f%%")
    show_table(view, column_config=cfg)
