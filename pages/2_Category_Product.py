"""Page 2 — Category & Product Performance."""
import plotly.express as px
import streamlit as st

from utils.data_processing import category_insights, fmt_inr, fmt_num, fmt_pct, group_summary
from utils.ui import (color_map, lakh_table, get_data, insights_box, kpi_card, kpi_row, page_header,
                      profit_color, sales_color, show_chart, show_table, style_fig)

df, full_df = get_data()
cat = group_summary(df, "Category")
prod = group_summary(df, "Product")
cmap = color_map(full_df["Category"].unique())  # stable colours even when filtered

page_header("🛍️ Category & Product Performance",
            "Which categories and products are driving the business?")

best_cat = cat.iloc[0]
best_prod = prod.sort_values("Profit", ascending=False).iloc[0]
kpi_row([
    kpi_card("Categories", fmt_num(len(cat)), f"{fmt_num(len(prod))} products", "🗂️"),
    kpi_card("Top Category", best_cat["Category"], f"{fmt_inr(best_cat['Sales'])} sales", "🏆", "good"),
    kpi_card("Most Profitable Product", best_prod["Product"],
             f"{fmt_inr(best_prod['Profit'])} profit", "⭐", "good"),
    kpi_card("Top-10 Product Share", fmt_pct(prod.head(10)["Sales"].sum() / prod["Sales"].sum() * 100),
             "of total sales", "📊", "info"),
])

# ---------------- Category charts ----------------
c1, c2, c3 = st.columns(3)
for col, metric, title, fmt in [
    (c1, "Sales", "Category-wise Sales", fmt_inr),
    (c2, "Profit", "Category-wise Profit", fmt_inr),
    (c3, "Units", "Category-wise Units Sold", fmt_num),
]:
    with col:
        d = cat.sort_values(metric)
        d["Text"] = d[metric].map(fmt)
        fig = px.bar(d, x=metric, y="Category", orientation="h", color="Category",
                     color_discrete_map=cmap, text="Text", title=title,
                     labels={metric: "", "Category": ""})
        prefix = "₹" if metric != "Units" else ""
        fig.update_traces(textposition="outside", cliponaxis=False, marker_cornerradius=4,
                          hovertemplate=f"%{{y}}<br>{metric} {prefix}%{{x:,.0f}}<extra></extra>")
        fig.update_xaxes(showticklabels=False, range=[0, d[metric].max() * 1.5])
        show_chart(style_fig(fig, height=360, legend=False))

# ---------------- Products ----------------
c4, c5 = st.columns(2)
with c4:
    top = prod.head(10).sort_values("Sales")
    top["Text"] = top["Sales"].map(fmt_inr)
    fig = px.bar(top, x="Sales", y="Product", orientation="h", text="Text",
                 title="Top 10 Products by Sales", labels={"Sales": "", "Product": ""},
                 custom_data=["Units", "Margin_%"])
    fig.update_traces(marker_color=sales_color(), textposition="outside", cliponaxis=False,
                      marker_cornerradius=4,
                      hovertemplate="%{y}<br>Sales ₹%{x:,.0f}<br>Units %{customdata[0]:,}"
                                    "<br>Margin %{customdata[1]:.1f}%<extra></extra>")
    fig.update_xaxes(showticklabels=False, range=[0, top["Sales"].max() * 1.4])
    show_chart(style_fig(fig, height=430, legend=False))
with c5:
    topp = prod.sort_values("Profit", ascending=False).head(10).sort_values("Profit")
    topp["Text"] = topp["Profit"].map(fmt_inr)
    fig = px.bar(topp, x="Profit", y="Product", orientation="h", text="Text",
                 title="Top 10 Products by Profit", labels={"Profit": "", "Product": ""},
                 custom_data=["Margin_%"])
    fig.update_traces(marker_color=profit_color(), textposition="outside", cliponaxis=False,
                      marker_cornerradius=4,
                      hovertemplate="%{y}<br>Profit ₹%{x:,.0f}<br>Margin %{customdata[0]:.1f}%"
                                    "<extra></extra>")
    fig.update_xaxes(showticklabels=False, range=[0, topp["Profit"].max() * 1.4])
    show_chart(style_fig(fig, height=430, legend=False))

# Product contribution: treemap (category -> product) sized by sales
pc = (df.groupby(["Category", "Product"])
        .agg(Sales=("Total_Sales_INR", "sum"), Profit=("Profit_INR", "sum"))
        .reset_index())
pc["Share"] = pc["Sales"] / pc["Sales"].sum() * 100
fig = px.treemap(pc, path=[px.Constant("All products"), "Category", "Product"], values="Sales",
                 color="Category", color_discrete_map={**cmap, "(?)": "#9CA3AF"},
                 title="Product Contribution % of Sales (click a category to zoom)",
                 custom_data=["Share"])
fig.update_traces(texttemplate="%{label}<br>%{percentRoot:.1%}",
                  hovertemplate="%{label}<br>Sales ₹%{value:,.0f}<br>%{percentRoot:.2%} of total"
                                "<extra></extra>",
                  marker=dict(line=dict(width=2)), root_color="rgba(0,0,0,0)")
show_chart(style_fig(fig, height=520, legend=False))

insights_box(category_insights(df))

with st.expander("📋 Product performance table"):
    view = prod[["Product", "Sales", "Profit", "Margin_%", "Units", "Orders",
                 "Sales_Share_%", "Return_Rate_%"]]
    view, cfg = lakh_table(view, ["Sales", "Profit"])
    show_table(view, column_config={
        **cfg,
        "Margin_%": st.column_config.NumberColumn("Margin %", format="%.1f%%"),
        "Sales_Share_%": st.column_config.ProgressColumn(
            "Sales share", format="%.1f%%", min_value=0, max_value=float(view["Sales_Share_%"].max())),
        "Return_Rate_%": st.column_config.NumberColumn("Return rate", format="%.1f%%"),
    })
