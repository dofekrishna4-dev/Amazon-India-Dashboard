"""Page 4 — Payment & Fulfillment Analysis."""
import plotly.express as px
import streamlit as st

from utils.data_processing import fmt_inr, fmt_pct, group_summary, payment_insights
from utils.ui import (color_map, get_data, insights_box, kpi_card, kpi_row, page_header,
                      section, show_chart, show_table, style_fig, theme)

df, full_df = get_data()
t = theme()
pay = group_summary(df, "Payment_Method")
ful = group_summary(df, "Fulfillment")
pmap = color_map(full_df["Payment_Method"].unique())
fmap = color_map(full_df["Fulfillment"].unique())

page_header("💳 Payment & Fulfillment Analysis",
            "How do customers pay, and which fulfilment channels generate the business?")

top_pay = pay.sort_values("Orders", ascending=False).iloc[0]
top_ful = ful.iloc[0]
cod = pay[pay["Payment_Method"].str.contains("COD|Cash", case=False)]
digital_share = (1 - cod["Orders"].sum() / pay["Orders"].sum()) * 100
kpi_row([
    kpi_card("Most Used Payment", top_pay["Payment_Method"],
             f"{fmt_pct(top_pay['Orders'] / pay['Orders'].sum() * 100)} of orders", "📱", "info"),
    kpi_card("Digital Payments", fmt_pct(digital_share), "Orders not paid by cash", "💳", "good"),
    kpi_card("Top Fulfillment", top_ful["Fulfillment"], f"{fmt_pct(top_ful['Sales_Share_%'])} of sales", "🏬"),
    kpi_card("Best Channel Margin", fmt_pct(ful["Margin_%"].max()),
             ful.sort_values("Margin_%").iloc[-1]["Fulfillment"], "🎯", "good"),
])


def hbar(d, metric, by, cmap, title, height=340):
    d = d.sort_values(metric)
    d = d.assign(Text=d[metric].map(fmt_inr))
    fig = px.bar(d, x=metric, y=by, orientation="h", color=by, color_discrete_map=cmap,
                 text="Text", title=title, labels={metric: "", by: ""})
    fig.update_traces(textposition="outside", cliponaxis=False, marker_cornerradius=4,
                      hovertemplate=f"%{{y}}<br>{metric} ₹%{{x:,.0f}}<extra></extra>")
    fig.update_xaxes(showticklabels=False, range=[0, d[metric].max() * 1.5])
    return style_fig(fig, height=height, legend=False)


section("Payment methods")
c1, c2 = st.columns(2)
with c1:
    show_chart(hbar(pay, "Sales", "Payment_Method", pmap, "Sales by Payment Method"))
with c2:
    show_chart(hbar(pay, "Profit", "Payment_Method", pmap, "Profit by Payment Method"))

c3, c4 = st.columns([1, 1.3])
with c3:
    fig = px.pie(pay, names="Payment_Method", values="Orders", hole=0.55, color="Payment_Method",
                 color_discrete_map=pmap, title="Payment Method Share % (orders)")
    fig.update_traces(textinfo="percent", marker=dict(line=dict(color=t["surface"], width=2)),
                      hovertemplate="%{label}<br>%{value:,} orders (%{percent})<extra></extra>")
    fig = style_fig(fig, height=380)
    fig.update_layout(margin=dict(t=55, r=10),
                      legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02))
    show_chart(fig)
with c4:
    mix = df.groupby(["Category", "Payment_Method"]).size().reset_index(name="Orders")
    mix["Share"] = mix["Orders"] / mix.groupby("Category")["Orders"].transform("sum") * 100
    fig = px.bar(mix, x="Share", y="Category", color="Payment_Method", orientation="h",
                 color_discrete_map=pmap, title="Payment Mix by Category (% of orders)",
                 labels={"Share": "", "Category": "", "Payment_Method": ""})
    fig.update_traces(marker_line=dict(color=t["surface"], width=2),
                      hovertemplate="%{y}<br>%{fullData.name}: %{x:.1f}%<extra></extra>")
    fig.update_layout(barmode="stack")
    fig.update_xaxes(ticksuffix="%")
    fig = style_fig(fig, height=400)
    fig.update_layout(margin=dict(t=55, b=10),
                      legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0))
    show_chart(fig)

section("Fulfillment methods")
c5, c6, c7 = st.columns(3)
with c5:
    show_chart(hbar(ful, "Sales", "Fulfillment", fmap, "Sales by Fulfillment Method", 300))
with c6:
    show_chart(hbar(ful, "Profit", "Fulfillment", fmap, "Profit by Fulfillment Method", 300))
with c7:
    d = ful.sort_values("Return_Rate_%")
    fig = px.bar(d, x=["Return_Rate_%", "Cancel_Rate_%"], y="Fulfillment", barmode="group",
                 orientation="h", title="Return & Cancel Rate by Channel",
                 color_discrete_sequence=["#fab219", "#d03b3b"],
                 labels={"value": "", "Fulfillment": "", "variable": ""})
    fig.for_each_trace(lambda tr: tr.update(name="Return rate" if "Return" in tr.name else "Cancel rate"))
    fig.update_traces(marker_cornerradius=4,
                      hovertemplate="%{y}<br>%{fullData.name}: %{x:.1f}%<extra></extra>")
    fig.update_xaxes(ticksuffix="%")
    fig = style_fig(fig, height=320)
    fig.update_layout(margin=dict(t=55, b=10),
                      legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0))
    show_chart(fig)

insights_box(payment_insights(df))

tab1, tab2 = st.tabs(["📋 Payment table", "📋 Fulfillment table"])
cfg = {
    "Sales": st.column_config.NumberColumn("Sales (₹ L)", format="%.2f"),
    "Profit": st.column_config.NumberColumn("Profit (₹ L)", format="%.2f"),
    "AOV": st.column_config.NumberColumn("Avg order (₹)", format="%.0f"),
    "Margin_%": st.column_config.NumberColumn("Margin %", format="%.1f%%"),
    "Sales_Share_%": st.column_config.NumberColumn("Sales share", format="%.1f%%"),
    "Return_Rate_%": st.column_config.NumberColumn("Return rate", format="%.1f%%"),
}
with tab1:
    show_table(pay.assign(Sales=pay["Sales"] / 1e5, Profit=pay["Profit"] / 1e5)[["Payment_Method", "Orders", "Sales", "Profit", "AOV", "Margin_%",
                    "Sales_Share_%", "Return_Rate_%"]], column_config=cfg)
with tab2:
    show_table(ful.assign(Sales=ful["Sales"] / 1e5, Profit=ful["Profit"] / 1e5)[["Fulfillment", "Orders", "Sales", "Profit", "AOV", "Margin_%",
                    "Sales_Share_%", "Return_Rate_%"]], column_config=cfg)