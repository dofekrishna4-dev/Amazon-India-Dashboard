"""Page 5 — Geographic Performance across Indian states."""
import plotly.express as px
import streamlit as st

from utils.data_processing import (STATE_COORDS, fmt_inr, fmt_num, fmt_pct, geo_insights,
                                   group_summary)
from utils.ui import (get_data, lakh_table, insights_box, kpi_card, kpi_row, page_header, profit_color,
                      sales_color, section, show_chart, show_table, style_fig, theme)

df, full_df = get_data()
t = theme()
st_df = group_summary(df, "Ship_State")
reg = group_summary(df, "Region")

page_header("🗺️ Geographic Performance",
            "Which states and regions of India generate the most business?")

top = st_df.iloc[0]
kpi_row([
    kpi_card("States Served", fmt_num(len(st_df)), f"across {len(reg)} regions", "📍"),
    kpi_card("Top State (Sales)", top["Ship_State"], f"{fmt_inr(top['Sales'])} · {fmt_pct(top['Sales_Share_%'])}", "🏆", "good"),
    kpi_card("Top State (Profit)", st_df.sort_values("Profit").iloc[-1]["Ship_State"],
             fmt_inr(st_df["Profit"].max()), "💰", "good"),
    kpi_card("Top Region", reg.iloc[0]["Region"], f"{fmt_pct(reg.iloc[0]['Sales_Share_%'])} of sales", "🧭", "info"),
])

# ---------------- India map ----------------
geo = st_df.copy()
geo["lat"] = geo["Ship_State"].map(lambda s: STATE_COORDS.get(s, (None, None))[0])
geo["lon"] = geo["Ship_State"].map(lambda s: STATE_COORDS.get(s, (None, None))[1])
geo = geo.dropna(subset=["lat", "lon"])
geo["Sales_txt"] = geo["Sales"].map(fmt_inr)

c0, c00 = st.columns([1.3, 1])
with c0:
    fig = px.scatter_geo(geo, lat="lat", lon="lon", size="Sales", color="Margin_%",
                         hover_name="Ship_State", text="Ship_State", size_max=48,
                         color_continuous_scale=t["seq"],
                         custom_data=["Sales_txt", "Orders", "Margin_%"],
                         title="India Sales Map (bubble = sales, colour = margin %)")
    fig.update_traces(textposition="top center",
                      textfont=dict(size=11, color=t["text"]),
                      marker=dict(line=dict(color=t["surface"], width=2), opacity=0.9),
                      hovertemplate="<b>%{hovertext}</b><br>Sales %{customdata[0]}"
                                    "<br>Orders %{customdata[1]:,}<br>Margin %{customdata[2]:.1f}%"
                                    "<extra></extra>")
    fig.update_geos(scope="asia", lataxis_range=[6, 36], lonaxis_range=[67, 98],
                    showcountries=True, countrycolor=t["border"], showland=True,
                    landcolor=t["surface_2"], showocean=True, oceancolor=t["surface"],
                    bgcolor=t["surface"], showframe=False, showcoastlines=True,
                    coastlinecolor=t["border"])
    fig.update_layout(coloraxis_colorbar=dict(title="Margin %", ticksuffix="%", thickness=12))
    show_chart(style_fig(fig, height=520, legend=False))
with c00:
    rd = reg.sort_values("Sales").assign(Text=lambda d: d["Sales"].map(fmt_inr))
    fig = px.bar(rd, x="Sales", y="Region", orientation="h", text="Text",
                 title="Sales by Region", labels={"Sales": "", "Region": ""})
    fig.update_traces(marker_color=sales_color(), textposition="outside", cliponaxis=False,
                      marker_cornerradius=4, hovertemplate="%{y}<br>₹%{x:,.0f}<extra></extra>")
    fig.update_xaxes(showticklabels=False, range=[0, reg["Sales"].max() * 1.45])
    show_chart(style_fig(fig, height=250, legend=False))

    tree = df.groupby(["Region", "Ship_State"])["Total_Sales_INR"].sum().reset_index()
    fig = px.sunburst(tree, path=["Region", "Ship_State"], values="Total_Sales_INR",
                      color_discrete_sequence=t["series"], title="Region → State Sales Share")
    fig.update_traces(hovertemplate="%{label}<br>₹%{value:,.0f} (%{percentRoot:.1%})<extra></extra>",
                      marker=dict(line=dict(color=t["surface"], width=2)))
    show_chart(style_fig(fig, height=260, legend=False))

# ---------------- State charts ----------------
section("State-wise performance")
c1, c2, c3 = st.columns(3)
for col, metric, title, color, fmt in [
    (c1, "Sales", "State-wise Sales", sales_color(), fmt_inr),
    (c2, "Profit", "State-wise Profit", profit_color(), fmt_inr),
    (c3, "Orders", "State-wise Orders", t["series"][6], fmt_num),
]:
    with col:
        d = st_df.sort_values(metric)
        d = d.assign(Text=d[metric].map(fmt))
        fig = px.bar(d, x=metric, y="Ship_State", orientation="h", text="Text", title=title,
                     labels={metric: "", "Ship_State": ""})
        prefix = "₹" if metric != "Orders" else ""
        fig.update_traces(marker_color=color, textposition="outside", cliponaxis=False,
                          marker_cornerradius=4,
                          hovertemplate=f"%{{y}}<br>{metric} {prefix}%{{x:,.0f}}<extra></extra>")
        fig.update_xaxes(showticklabels=False, range=[0, d[metric].max() * 1.55])
        show_chart(style_fig(fig, height=420, legend=False))

c4, c5 = st.columns(2)
for col, metric, title, color in [(c4, "Sales", "Top 10 States by Sales", sales_color()),
                                  (c5, "Profit", "Top 10 States by Profit", profit_color())]:
    with col:
        d = st_df.sort_values(metric, ascending=False).head(10).reset_index(drop=True)
        d["Rank"] = [f"#{i + 1}" for i in range(len(d))]
        fig = px.bar(d, x="Ship_State", y=metric, title=title,
                     labels={"Ship_State": "", metric: f"{metric} (₹)"}, custom_data=["Rank"])
        fig.update_traces(marker_color=color, marker_cornerradius=4,
                          hovertemplate="%{customdata[0]} %{x}<br>₹%{y:,.0f}<extra></extra>")
        fig.update_xaxes(tickangle=-35)
        show_chart(style_fig(fig, height=380, legend=False, inr_max=d[metric].max()))

# ---------------- State x category heatmap ----------------
hm = df.pivot_table(index="Ship_State", columns="Category", values="Total_Sales_INR",
                    aggfunc="sum", fill_value=0)
hm = hm.loc[hm.sum(axis=1).sort_values(ascending=False).index]
fig = px.imshow(hm / 1e5, aspect="auto", color_continuous_scale=t["seq"],
                text_auto=".1f", title="India State Analysis — Sales by State × Category (₹ Lakh)",
                labels=dict(x="", y="", color="₹ L"))
fig.update_traces(hovertemplate="%{y} · %{x}<br>₹%{z:.2f} L<extra></extra>")
show_chart(style_fig(fig, height=460, legend=False))

insights_box(geo_insights(df))

with st.expander("📋 State performance table"):
    view, cfg = lakh_table(st_df[["Ship_State", "Sales", "Profit", "Orders", "Units", "Margin_%",
                                  "Sales_Share_%", "Return_Rate_%", "Cancel_Rate_%", "AOV"]],
                           ["Sales", "Profit"])
    show_table(view,
               column_config={
                   **cfg,
                   "Ship_State": "State",
                   "AOV": st.column_config.NumberColumn("Avg order (₹)", format="%.0f"),
                   "Margin_%": st.column_config.NumberColumn("Margin %", format="%.1f%%"),
                   "Sales_Share_%": st.column_config.ProgressColumn(
                       "Sales share", format="%.1f%%", min_value=0,
                       max_value=float(st_df["Sales_Share_%"].max())),
                   "Return_Rate_%": st.column_config.NumberColumn("Return rate", format="%.1f%%"),
                   "Cancel_Rate_%": st.column_config.NumberColumn("Cancel rate", format="%.1f%%"),
               })
