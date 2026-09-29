"""
Downloadable reports:
  * build_html_report  -> a self-contained HTML management report (KPIs, insights, charts)
  * build_excel_report -> a formatted multi-sheet Excel workbook built with OpenPyXL
"""
from __future__ import annotations

import html
import io
import re
from datetime import datetime

import pandas as pd
import plotly.express as px
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from utils.data_processing import (
    all_insights, compute_kpis, fmt_inr, fmt_num, fmt_pct, group_summary,
    lost_revenue_by, monthly_summary,
)

PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
STATUS = {"Delivered": "#0ca30c", "Shipped": "#2a78d6", "Returned": "#fab219", "Cancelled": "#d03b3b"}


def _md_bold_to_html(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(text))


def _fig_html(fig, first: bool) -> str:
    fig.update_layout(template="plotly_white", height=360,
                      margin=dict(l=10, r=10, t=50, b=10),
                      font=dict(family="Inter, Segoe UI, Arial", size=12),
                      legend=dict(orientation="h", y=1.02, yanchor="bottom", x=1, xanchor="right"))
    return fig.to_html(full_html=False, include_plotlyjs="cdn" if first else False,
                       config={"displaylogo": False, "responsive": True})


def build_html_report(df: pd.DataFrame, filters_text: str) -> bytes:
    k = compute_kpis(df)
    ins = all_insights(df)
    m = monthly_summary(df)
    cat = group_summary(df, "Category")
    prod = group_summary(df, "Product").head(10)
    pay = group_summary(df, "Payment_Method")
    ful = group_summary(df, "Fulfillment")
    state = group_summary(df, "Ship_State")
    status = df["Order_Status"].value_counts().reset_index()
    status.columns = ["Order_Status", "Orders"]

    ml = m.melt(id_vars="Year_Month", value_vars=["Sales", "Profit"], var_name="Measure", value_name="INR")
    figs = [
        px.line(ml, x="Year_Month", y="INR", color="Measure", markers=True,
                color_discrete_map={"Sales": PALETTE[0], "Profit": PALETTE[2]},
                title="Monthly Sales & Profit Trend", labels={"Year_Month": "", "INR": "₹"}),
        px.bar(cat, x="Category", y="Sales", color="Category", title="Sales by Category",
               color_discrete_sequence=PALETTE, labels={"Sales": "Sales (₹)", "Category": ""}),
        px.bar(prod.sort_values("Sales"), x="Sales", y="Product", orientation="h",
               title="Top 10 Products by Sales", color_discrete_sequence=[PALETTE[0]],
               labels={"Sales": "Sales (₹)", "Product": ""}),
        px.pie(status, names="Order_Status", values="Orders", hole=0.55,
               title="Order Status Distribution", color="Order_Status", color_discrete_map=STATUS),
        px.bar(pay, x="Payment_Method", y="Sales", title="Sales by Payment Method",
               color="Payment_Method", color_discrete_sequence=PALETTE,
               labels={"Sales": "Sales (₹)", "Payment_Method": ""}),
        px.bar(state.sort_values("Sales"), x="Sales", y="Ship_State", orientation="h",
               title="Sales by State", color_discrete_sequence=[PALETTE[0]],
               labels={"Sales": "Sales (₹)", "Ship_State": ""}),
    ]
    for f in figs[1:3] + figs[4:]:
        f.update_layout(showlegend=False)
    charts = "".join(f'<div class="chart">{_fig_html(f, i == 0)}</div>' for i, f in enumerate(figs))

    kpis = [
        ("Total Sales", fmt_inr(k["total_sales"])), ("Total Profit", fmt_inr(k["total_profit"])),
        ("Total Orders", fmt_num(k["total_orders"])), ("Units Sold", fmt_num(k["total_units"])),
        ("Avg Order Value", fmt_inr(k["aov"])), ("Profit Margin", fmt_pct(k["profit_margin"])),
        ("Return Rate", fmt_pct(k["return_rate"])), ("Cancellation Rate", fmt_pct(k["cancel_rate"])),
        ("Revenue Lost", fmt_inr(k["lost_total"])), ("Net Sales", fmt_inr(k["net_sales"])),
    ]
    kpi_html = "".join(f'<div class="kpi"><div class="l">{a}</div><div class="v">{b}</div></div>'
                       for a, b in kpis)
    ins_html = "".join(
        f"<h3>{html.escape(sec)}</h3><ul>" + "".join(f"<li>{_md_bold_to_html(x)}</li>" for x in items) + "</ul>"
        for sec, items in ins.items() if items)

    def table(t: pd.DataFrame, cols: list[str]) -> str:
        t = t[cols].copy()
        for c in t.columns:
            if c in ("Sales", "Profit", "AOV"):
                t[c] = t[c].map(fmt_inr)
            elif c.endswith("%"):
                t[c] = t[c].map(lambda v: f"{v:.1f}%")
            elif c in ("Orders", "Units"):
                t[c] = t[c].map(fmt_num)
        return t.to_html(index=False, classes="tbl", border=0, escape=True)

    period = f"{df['Order_Date'].min():%d %b %Y} – {df['Order_Date'].max():%d %b %Y}"
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Amazon India Dashboard Report</title>
<style>
body{{font-family:Inter,Segoe UI,Arial,sans-serif;background:#F3F4F6;color:#0F1111;margin:0}}
.wrap{{max-width:1200px;margin:0 auto;padding:24px 16px}}
header{{background:linear-gradient(90deg,#232F3E,#131921);color:#fff;border-radius:14px;padding:22px 24px;border-bottom:4px solid #FF9900}}
header h1{{margin:0;font-size:26px}} header p{{margin:4px 0 0;color:#D1D5DB;font-size:14px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:18px 0}}
.kpi{{background:#fff;border:1px solid #E5E7EB;border-top:4px solid #FF9900;border-radius:12px;padding:12px 14px}}
.kpi .l{{font-size:12px;color:#6B7280;text-transform:uppercase;font-weight:600;letter-spacing:.04em}}
.kpi .v{{font-size:22px;font-weight:800;margin-top:4px}}
.card{{background:#fff;border:1px solid #E5E7EB;border-radius:12px;padding:16px 20px;margin:14px 0}}
.charts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(460px,1fr));gap:14px}}
.chart{{background:#fff;border:1px solid #E5E7EB;border-radius:12px;padding:6px}}
h2{{font-size:20px;margin:26px 0 6px}} h3{{font-size:16px;margin:14px 0 4px;color:#232F3E}}
li{{margin:4px 0;line-height:1.45}}
.tbl{{border-collapse:collapse;width:100%;font-size:13px}}
.tbl th{{background:#232F3E;color:#fff;text-align:left;padding:8px}}
.tbl td{{padding:7px 8px;border-bottom:1px solid #E5E7EB}}
.tbl tr:nth-child(even) td{{background:#F9FAFB}}
footer{{color:#6B7280;font-size:12px;margin-top:24px}}
@media(max-width:600px){{.charts{{grid-template-columns:1fr}}}}
@media print{{body{{background:#fff}} .chart,.card,.kpi{{break-inside:avoid}}}}
</style></head><body><div class="wrap">
<header><h1>Amazon India — Business Performance Report</h1>
<p>Period: {period} &nbsp;|&nbsp; Filters: {html.escape(filters_text)} &nbsp;|&nbsp;
Generated {datetime.now():%d %b %Y, %H:%M}</p></header>
<div class="kpis">{kpi_html}</div>
<div class="card"><h2 style="margin-top:0">Key business insights</h2>{ins_html}</div>
<h2>Charts</h2><div class="charts">{charts}</div>
<h2>Category performance</h2><div class="card">{table(cat, ["Category","Sales","Profit","Margin_%","Orders","Units","Return_Rate_%","Cancel_Rate_%"])}</div>
<h2>Top 10 products</h2><div class="card">{table(prod, ["Product","Sales","Profit","Margin_%","Units"])}</div>
<h2>Payment methods</h2><div class="card">{table(pay, ["Payment_Method","Sales","Profit","Orders","AOV","Return_Rate_%"])}</div>
<h2>Fulfillment</h2><div class="card">{table(ful, ["Fulfillment","Sales","Profit","Margin_%","Orders"])}</div>
<h2>States</h2><div class="card">{table(state, ["Ship_State","Sales","Profit","Orders","Margin_%","Return_Rate_%"])}</div>
<footer>Note: Total Sales is gross booked sales and includes returned and cancelled orders,
which carry zero profit. Net Sales excludes them.</footer>
</div></body></html>"""
    return doc.encode("utf-8")


# ---------------------------------------------------------------------------
# Excel report (OpenPyXL)
# ---------------------------------------------------------------------------
HEADER_FILL = PatternFill("solid", fgColor="232F3E")
ACCENT_FILL = PatternFill("solid", fgColor="FF9900")
ZEBRA_FILL = PatternFill("solid", fgColor="F3F4F6")
THIN = Side(style="thin", color="E5E7EB")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
INR_FMT = '"₹"#,##0'
PCT_FMT = '0.0"%"'


def _write_table(ws, t: pd.DataFrame, start_row: int = 1, money=(), pct=(), ints=()):
    for j, col in enumerate(t.columns, 1):
        c = ws.cell(row=start_row, column=j, value=str(col).replace("_", " "))
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = HEADER_FILL
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDER
    for i, row in enumerate(t.itertuples(index=False), start_row + 1):
        for j, val in enumerate(row, 1):
            if isinstance(val, pd.Timestamp):
                val = val.to_pydatetime()
            elif hasattr(val, "item"):
                val = val.item()
            c = ws.cell(row=i, column=j, value=val)
            c.border = BORDER
            name = t.columns[j - 1]
            if name in money:
                c.number_format = INR_FMT
            elif name in pct:
                c.number_format = PCT_FMT
            elif name in ints:
                c.number_format = "#,##0"
            elif isinstance(val, datetime):
                c.number_format = "mmm yyyy"
            if (i - start_row) % 2 == 0:
                c.fill = ZEBRA_FILL
    for j, col in enumerate(t.columns, 1):
        width = max([len(str(col))] + [len(str(v)) for v in t.iloc[:, j - 1].head(200)]) + 3
        ws.column_dimensions[get_column_letter(j)].width = min(max(width, 12), 40)
    ws.freeze_panes = ws.cell(row=start_row + 1, column=1)
    return start_row + len(t)


def _bar_chart(ws, title, cats_col, val_col, first_row, last_row, anchor, y_title="₹"):
    ch = BarChart()
    ch.type = "col"
    ch.title = title
    ch.y_axis.title = y_title
    ch.height, ch.width = 8, 16
    data = Reference(ws, min_col=val_col, min_row=first_row - 1, max_row=last_row)
    cats = Reference(ws, min_col=cats_col, min_row=first_row, max_row=last_row)
    ch.add_data(data, titles_from_data=True)
    ch.set_categories(cats)
    ch.legend = None
    ch.series[0].graphicalProperties.solidFill = "2A78D6"
    ws.add_chart(ch, anchor)


def build_excel_report(df: pd.DataFrame, filters_text: str) -> bytes:
    wb = Workbook()
    k = compute_kpis(df)

    # --- Summary sheet ---
    ws = wb.active
    ws.title = "Summary"
    ws["A1"] = "Amazon India — Business Performance Report"
    ws["A1"].font = Font(size=16, bold=True, color="FFFFFF")
    ws["A1"].fill = HEADER_FILL
    ws.merge_cells("A1:D1")
    ws["A2"] = f"Filters: {filters_text}"
    ws["A3"] = (f"Period: {df['Order_Date'].min():%d %b %Y} – {df['Order_Date'].max():%d %b %Y}   |   "
                f"Generated {datetime.now():%d %b %Y %H:%M}")
    ws["A2"].font = ws["A3"].font = Font(italic=True, color="6B7280")
    rows = [
        ("Total Sales", k["total_sales"], INR_FMT), ("Total Profit", k["total_profit"], INR_FMT),
        ("Total Orders", k["total_orders"], "#,##0"), ("Total Units Sold", k["total_units"], "#,##0"),
        ("Average Order Value", k["aov"], INR_FMT), ("Profit Margin %", k["profit_margin"], PCT_FMT),
        ("Delivered Orders", k["delivered"], "#,##0"), ("Shipped Orders", k["shipped"], "#,##0"),
        ("Returned Orders", k["returned"], "#,##0"), ("Cancelled Orders", k["cancelled"], "#,##0"),
        ("Return Rate %", k["return_rate"], PCT_FMT), ("Cancellation Rate %", k["cancel_rate"], PCT_FMT),
        ("Revenue Lost — Returns", k["lost_returns"], INR_FMT),
        ("Revenue Lost — Cancellations", k["lost_cancel"], INR_FMT),
        ("Net Sales (excl. returns & cancellations)", k["net_sales"], INR_FMT),
    ]
    ws["A5"], ws["B5"] = "KPI", "Value"
    for c in (ws["A5"], ws["B5"]):
        c.font = Font(bold=True, color="131921")
        c.fill = ACCENT_FILL
    for i, (label, val, fmt) in enumerate(rows, 6):
        ws.cell(row=i, column=1, value=label).border = BORDER
        c = ws.cell(row=i, column=2, value=float(val))
        c.number_format = fmt
        c.border = BORDER
        c.font = Font(bold=True)
    ws.column_dimensions["A"].width = 44
    ws.column_dimensions["B"].width = 20

    r = 6 + len(rows) + 1
    ws.cell(row=r, column=1, value="Key business insights").font = Font(size=13, bold=True)
    r += 1
    for sec, items in all_insights(df).items():
        ws.cell(row=r, column=1, value=sec).font = Font(bold=True, color="232F3E")
        r += 1
        for it in items:
            ws.cell(row=r, column=1, value="• " + it.replace("**", ""))
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
            r += 1

    money = ("Sales", "Profit", "AOV", "Returned_INR", "Cancelled_INR", "Total_Lost")
    pct = ("Margin_%", "Return_Rate_%", "Cancel_Rate_%", "Sales_Share_%")
    ints = ("Orders", "Units", "Returned", "Cancelled")

    # --- Monthly ---
    ws = wb.create_sheet("Monthly Trend")
    m = monthly_summary(df).rename(columns={"Year_Month": "Month"})
    last = _write_table(ws, m, money=money, pct=pct, ints=ints)
    lc = LineChart()
    lc.title, lc.height, lc.width = "Monthly Sales & Profit", 9, 22
    lc.add_data(Reference(ws, min_col=2, max_col=3, min_row=1, max_row=last), titles_from_data=True)
    lc.set_categories(Reference(ws, min_col=1, min_row=2, max_row=last))
    lc.x_axis.number_format = "mmm yy"
    ws.add_chart(lc, "H2")

    # --- Grouped sheets with a native bar chart each ---
    for sheet, by in [("Category", "Category"), ("Products", "Product"),
                      ("Payment Methods", "Payment_Method"), ("Fulfillment", "Fulfillment"),
                      ("States", "Ship_State")]:
        ws = wb.create_sheet(sheet)
        g = group_summary(df, by)
        last = _write_table(ws, g, money=money, pct=pct, ints=ints)
        _bar_chart(ws, f"Sales by {by.replace('_', ' ')}", 1, 2, 2, min(last, 11),
                   f"{get_column_letter(len(g.columns) + 2)}2")

    # --- Revenue loss ---
    ws = wb.create_sheet("Revenue Loss")
    lost = lost_revenue_by(df, "Category").rename(
        columns={"Returned": "Returned_INR", "Cancelled": "Cancelled_INR"})
    last = _write_table(ws, lost, money=money)
    if lost.empty:
        ws.cell(row=3, column=1, value="No returned or cancelled orders in this selection.")
    bc = BarChart()
    bc.type, bc.grouping, bc.overlap = "col", "stacked", 100
    bc.title, bc.height, bc.width = "Revenue lost by category", 8, 16
    bc.add_data(Reference(ws, min_col=2, max_col=3, min_row=1, max_row=last), titles_from_data=True)
    bc.set_categories(Reference(ws, min_col=1, min_row=2, max_row=last))
    if not lost.empty:
        ws.add_chart(bc, "G2")

    # --- Filtered raw data ---
    ws = wb.create_sheet("Filtered Data")
    cols = ["Order_ID", "Order_Date", "Category", "Product", "Quantity", "Unit_Price_INR",
            "Discount_Pct", "Total_Sales_INR", "Profit_INR", "Payment_Method",
            "Fulfillment", "Order_Status", "Ship_State"]
    raw = df[cols].copy()
    ws.append(cols)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = HEADER_FILL
    for row in raw.itertuples(index=False):
        ws.append([v.to_pydatetime() if isinstance(v, pd.Timestamp) else
                   (v.item() if hasattr(v, "item") else v) for v in row])
    for cell in ws["B"][1:]:
        cell.number_format = "dd-mmm-yyyy"
    for col in ("F", "H", "I"):
        for cell in ws[col][1:]:
            cell.number_format = INR_FMT
    for cell in ws["G"][1:]:
        cell.number_format = "0%"
    for j in range(1, len(cols) + 1):
        ws.column_dimensions[get_column_letter(j)].width = 18
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
