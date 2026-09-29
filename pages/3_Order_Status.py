"""Page 3 — Order Status & Revenue Loss."""
import plotly.express as px
import streamlit as st

from utils.data_processing import (STATUS_ORDER, compute_kpis, fmt_inr, fmt_num, fmt_pct,
                                   group_summary, lost_revenue_by, status_insights)
from utils.ui import (STATUS_COLORS, lakh_table, get_data, insights_box, kpi_card, kpi_row, page_header,
                      section, show_chart, show_table, style_fig, theme)

df, full_df = get_data()
k = compute_kpis(df)
t = theme()

page_header("📦 Order Status & Revenue Loss",
            "How many orders are completed successfully, and how much revenue is being lost?")

n = max(k["total_orders"], 1)
kpi_row([
    kpi_card("Delivered", fmt_num(k["delivered"]), f"{k['delivered'] / n * 100:.1f}% of orders", "✅", "good"),
    kpi_card("Shipped", fmt_num(k["shipped"]), f"{k['shipped'] / n * 100:.1f}% in transit", "🚚", "info"),
    kpi_card("Returned", fmt_num(k["returned"]), f"{fmt_inr(k['lost_returns'])} lost", "↩️", "warning"),
    kpi_card("Cancelled", fmt_num(k["cancelled"]), f"{fmt_inr(k['lost_cancel'])} lost", "✖️", "critical"),
])
kpi_row([
    kpi_card("Return Rate", fmt_pct(k["return_rate"]), "Returned ÷ total orders", "📉", "warning"),
    kpi_card("Cancellation Rate", fmt_pct(k["cancel_rate"]), "Cancelled ÷ total orders", "🚫", "critical"),
    kpi_card("Total Revenue Lost", fmt_inr(k["lost_total"]),
             f"{k['lost_total'] / max(k['total_sales'], 1) * 100:.1f}% of gross sales", "💸", "critical"),
    kpi_card("Net Sales", fmt_inr(k["net_sales"]), "Excluding returns & cancellations", "💰", "good"),
])

# ---------------- Status distribution ----------------
c1, c2 = st.columns([1, 1.4])
with c1:
    s = (df["Order_Status"].value_counts()
           .reindex(STATUS_ORDER).dropna().reset_index())
    s.columns = ["Status", "Orders"]
    fig = px.pie(s, names="Status", values="Orders", hole=0.58, color="Status",
                 color_discrete_map=STATUS_COLORS, title="Order Status Distribution",
                 category_orders={"Status": STATUS_ORDER})
    fig.update_traces(textinfo="percent", textposition="inside", sort=False,
                      insidetextorientation="horizontal",
                      marker=dict(line=dict(color=t["surface"], width=2)),
                      hovertemplate="%{label}<br>%{value:,} orders (%{percent})<extra></extra>")
    fig.add_annotation(text=f"<b>{fmt_num(k['total_orders'])}</b><br>orders", showarrow=False,
                       font=dict(size=16, color=t["text"]))
    fig = style_fig(fig, height=400)
    fig.update_layout(legend=dict(orientation="v", yanchor="middle", y=0.5, x=1.0,
                                  xanchor="left"), margin=dict(t=55, r=10))
    show_chart(fig)
with c2:
    m = (df.groupby(["Year_Month", "Order_Status"]).size().reset_index(name="Orders"))
    m = m[m["Order_Status"].isin(["Returned", "Cancelled"])]
    fig = px.line(m, x="Year_Month", y="Orders", color="Order_Status", markers=True,
                  color_discrete_map=STATUS_COLORS, title="Returns & Cancellations per Month",
                  labels={"Year_Month": "", "Orders": "Orders", "Order_Status": ""})
    fig.update_traces(line=dict(width=2), marker=dict(size=7),
                      hovertemplate="%{x|%b %Y}<br>%{fullData.name}: %{y}<extra></extra>")
    show_chart(style_fig(fig, height=400))

# ---------------- Category-wise returns / cancellations ----------------
cat = group_summary(df, "Category")
c3, c4 = st.columns(2)
for col, count_col, rate_col, status, title in [
    (c3, "Returned", "Return_Rate_%", "Returned", "Category-wise Returns"),
    (c4, "Cancelled", "Cancel_Rate_%", "Cancelled", "Category-wise Cancellations"),
]:
    with col:
        d = cat.sort_values(count_col)
        d["Text"] = d.apply(lambda r: f"{int(r[count_col])} · {r[rate_col]:.1f}%", axis=1)
        fig = px.bar(d, x=count_col, y="Category", orientation="h", text="Text", title=title,
                     labels={count_col: "Orders", "Category": ""})
        fig.update_traces(marker_color=STATUS_COLORS[status], textposition="outside",
                          cliponaxis=False, marker_cornerradius=4,
                          hovertemplate="%{y}<br>%{x} orders<extra></extra>")
        fig.update_xaxes(range=[0, (float(d[count_col].max()) or 1) * 1.55])
        show_chart(style_fig(fig, height=360, legend=False))
        st.caption("Label shows order count · rate within the category.")

# ---------------- Revenue lost ----------------
section("💸 Revenue lost", "Sales value of orders that were returned or cancelled.")
lost = lost_revenue_by(df, "Category")
c5, c6 = st.columns(2)
for col, status, title in [(c5, "Returned", "Revenue Lost due to Returns"),
                           (c6, "Cancelled", "Revenue Lost due to Cancellations")]:
    with col:
        d = lost.sort_values(status)
        d["Text"] = d[status].map(fmt_inr)
        fig = px.bar(d, x=status, y="Category", orientation="h", text="Text", title=title,
                     labels={status: "", "Category": ""})
        fig.update_traces(marker_color=STATUS_COLORS[status], textposition="outside",
                          cliponaxis=False, marker_cornerradius=4,
                          hovertemplate="%{y}<br>₹%{x:,.0f} lost<extra></extra>")
        top_val = float(d[status].max()) if len(d) else 0.0
        fig.update_xaxes(showticklabels=False, range=[0, (top_val or 1) * 1.5])
        show_chart(style_fig(fig, height=360, legend=False))

ml = (df[df["Is_Lost"]].groupby(["Year_Month", "Order_Status"])["Total_Sales_INR"].sum()
        .reset_index())
fig = px.bar(ml, x="Year_Month", y="Total_Sales_INR", color="Order_Status",
             color_discrete_map=STATUS_COLORS, title="Monthly Revenue Lost",
             labels={"Year_Month": "", "Total_Sales_INR": "Revenue lost (₹)", "Order_Status": ""})
fig.update_traces(hovertemplate="%{x|%b %Y}<br>%{fullData.name}: ₹%{y:,.0f}<extra></extra>",
                  marker_line=dict(color=t["surface"], width=1))
lost_peak = ml.groupby("Year_Month")["Total_Sales_INR"].sum().max() if len(ml) else 0
show_chart(style_fig(fig, height=360, inr_max=lost_peak))

insights_box(status_insights(df))

with st.expander("📋 Returns & cancellations by category"):
    view = cat[["Category", "Orders", "Returned", "Return_Rate_%", "Cancelled", "Cancel_Rate_%"]] \
        .merge(lost[["Category", "Returned", "Cancelled", "Total_Lost"]]
               .rename(columns={"Returned": "Returned ₹", "Cancelled": "Cancelled ₹"}),
               on="Category", how="left").fillna(0)
    view, cfg = lakh_table(view, ["Returned ₹", "Cancelled ₹", "Total_Lost"])
    show_table(view, column_config={**cfg,
        "Return_Rate_%": st.column_config.NumberColumn("Return rate", format="%.1f%%"),
        "Cancel_Rate_%": st.column_config.NumberColumn("Cancel rate", format="%.1f%%"),
    })
