"""
Shared UI helpers: theme colours, CSS injection, KPI cards, chart styling
and a Streamlit-version-safe way to render charts and tables.
"""
from __future__ import annotations

import math
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

ASSETS = Path(__file__).resolve().parent.parent / "assets"

# Amazon brand accents (used for chrome: headers, card borders, buttons)
AMAZON_ORANGE = "#FF9900"
AMAZON_NAVY = "#131921"
AMAZON_SQUID = "#232F3E"

# Theme tokens --------------------------------------------------------------
THEMES = {
    "light": {
        "bg": "#F3F4F6", "surface": "#FFFFFF", "surface_2": "#F8FAFC",
        "text": "#0F1111", "text_2": "#4B5563", "muted": "#6B7280",
        "border": "#E5E7EB", "grid": "#E5E7EB",
        "sidebar": AMAZON_SQUID, "sidebar_text": "#FFFFFF",
        "plotly_template": "plotly_white",
        # validated categorical palette (fixed order, light steps)
        "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
                   "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
        "seq": ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#104281"],
    },
    "dark": {
        "bg": "#0F1419", "surface": "#1a1a19", "surface_2": "#22262B",
        "text": "#FFFFFF", "text_2": "#C3C2B7", "muted": "#9CA3AF",
        "border": "#2F3640", "grid": "#2F3640",
        "sidebar": AMAZON_NAVY, "sidebar_text": "#FFFFFF",
        "plotly_template": "plotly_dark",
        "series": ["#3987e5", "#d95926", "#199e70", "#c98500",
                   "#d55181", "#008300", "#9085e9", "#e66767"],
        "seq": ["#184f95", "#256abf", "#3987e5", "#6da7ec", "#b7d3f6"],
    },
}

# Status colours are fixed across themes and never reused for series.
STATUS_COLORS = {
    "Delivered": "#0ca30c",
    "Shipped": "#2a78d6",
    "Returned": "#fab219",
    "Cancelled": "#d03b3b",
}


def theme() -> dict:
    mode = st.session_state.get("theme_mode", "light")
    return THEMES[mode]


def color_map(values) -> dict:
    """Stable entity -> colour mapping (colour follows the entity, not its rank)."""
    pal = theme()["series"]
    return {v: pal[i % len(pal)] for i, v in enumerate(sorted(values))}


def sales_color() -> str:
    return theme()["series"][0]


def profit_color() -> str:
    return theme()["series"][2]


# CSS ---------------------------------------------------------------------------
def inject_css():
    t = theme()
    css_template = (ASSETS / "style.css").read_text(encoding="utf-8")
    css = css_template
    for key, val in {**t, "orange": AMAZON_ORANGE, "navy": AMAZON_NAVY,
                     "squid": AMAZON_SQUID}.items():
        if isinstance(val, str):
            css = css.replace(f"{{{{{key}}}}}", val)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    st.markdown(
        f"""<div class="page-header">
              <div class="page-title">{title}</div>
              <div class="page-subtitle">{subtitle}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, sub: str = "", icon: str = "", tone: str = ""):
    tone_cls = f" tone-{tone}" if tone else ""
    # Names (e.g. "Electronics & Mobiles") get a smaller font than numbers.
    first = str(value).lstrip()[:1]
    if not (first.isdigit() or first in "₹-+"):
        tone_cls += " kpi-text"
    return f"""<div class="kpi-card{tone_cls}">
                  <div class="kpi-top"><span class="kpi-label">{label}</span>
                  <span class="kpi-icon">{icon}</span></div>
                  <div class="kpi-value">{value}</div>
                  <div class="kpi-sub">{sub}</div>
               </div>"""


def kpi_row(cards: list[str]):
    """Render a list of kpi_card() HTML strings as a responsive grid."""
    st.markdown(f'<div class="kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def section(title: str, caption: str = ""):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    if caption:
        st.markdown(f'<div class="section-caption">{caption}</div>', unsafe_allow_html=True)


def insights_box(items: list[str], title: str = "💡 Business insights"):
    if not items:
        return
    with st.container(border=True):
        st.markdown(f"#### {title}")
        for it in items:
            st.markdown(f"- {it}")


# Charts ------------------------------------------------------------------------
def _nice_step(raw: float) -> float:
    if raw <= 0:
        return 1.0
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def inr_short(v: float) -> str:
    """Compact Indian-unit tick label: ₹0, ₹50 K, ₹20 L, ₹1.5 Cr."""
    if v == 0:
        return "₹0"
    for div, unit in ((1e7, "Cr"), (1e5, "L"), (1e3, "K")):
        if abs(v) >= div:
            return f"₹{v / div:.2f}".rstrip("0").rstrip(".") + f" {unit}"
    return f"₹{v:,.0f}"


def set_inr_axis(fig: go.Figure, max_val: float, axis: str = "y", ticks: int = 5):
    """Label a rupee axis in Lakh / Crore instead of Plotly's M / k."""
    if not max_val or max_val <= 0:
        return fig
    step = _nice_step(max_val / ticks)
    vals = [i * step for i in range(int(max_val // step) + 2)]
    upd = dict(tickvals=vals, ticktext=[inr_short(v) for v in vals],
               range=[0, max(vals[-1], max_val * 1.05)])
    (fig.update_yaxes if axis == "y" else fig.update_xaxes)(**upd)
    return fig


def style_fig(fig: go.Figure, height: int = 380, legend: bool = True,
              yprefix: str = "", inr_max: float | None = None) -> go.Figure:
    t = theme()
    fig.update_layout(
        template=t["plotly_template"],
        height=height,
        margin=dict(l=10, r=30, t=95 if legend else 55, b=10),
        paper_bgcolor=t["surface"],
        plot_bgcolor=t["surface"],
        font=dict(family="Inter, Segoe UI, Arial, sans-serif", size=13, color=t["text_2"]),
        title=dict(font=dict(size=16, color=t["text"]), x=0.01, xanchor="left"),
        hoverlabel=dict(font_size=13),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    title_text="", font=dict(color=t["text_2"])),
        bargap=0.25,
    )
    fig.update_xaxes(showgrid=False, linecolor=t["border"], zeroline=False,
                     title_font=dict(color=t["muted"]), tickfont=dict(color=t["text_2"]))
    fig.update_yaxes(gridcolor=t["grid"], zeroline=False, tickprefix=yprefix,
                     title_font=dict(color=t["muted"]), tickfont=dict(color=t["text_2"]))
    if inr_max:
        set_inr_axis(fig, inr_max, "y")
    return fig


def _st_version() -> tuple:
    try:
        return tuple(int(x) for x in st.__version__.split(".")[:2])
    except Exception:
        return (1, 40)


# Streamlit 1.50 replaced use_container_width with width="stretch".
_NEW_WIDTH_API = _st_version() >= (1, 50)


def show_chart(fig: go.Figure):
    """Render a Plotly chart full-width on any supported Streamlit version."""
    cfg = {"displaylogo": False, "responsive": True}
    if _NEW_WIDTH_API:
        st.plotly_chart(fig, width="stretch", config=cfg)
    else:
        st.plotly_chart(fig, use_container_width=True, config=cfg)


def show_table(df, **kwargs):
    if _NEW_WIDTH_API:
        st.dataframe(df, width="stretch", hide_index=True, **kwargs)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True, **kwargs)


def lakh_table(df, cols):
    """Copy of df with rupee columns converted to ₹ Lakh (sortable, readable)."""
    out = df.copy()
    cfg = {}
    for c in cols:
        if c in out.columns:
            out[c] = out[c] / 1e5
            label = c.replace("_", " ")
            cfg[c] = st.column_config.NumberColumn(f"{label} (₹ L)", format="%.2f")
    return out, cfg


def get_data():
    """Filtered data prepared by app.py for the current run."""
    return st.session_state["filtered_df"], st.session_state["full_df"]
