"""
Visualization — 7 auto-generated business charts using DataProfile.
Custom builder is secondary. Loading spinner visible between click and output.
"""
import dash
from dash import html, dcc, Input, Output, State, ctx
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import io
import base64
from services.insights_agent import DataProfile, _coerce, _series, _fmt, _pct, _chg

dash.register_page(__name__, path="/visualization", name="Visualization")

BRAND = "#3e8865"
CFG   = {"displaylogo": False, "responsive": True,
          "toImageButtonOptions": {"format": "png", "filename": "dericbi_chart", "scale": 2}}


def _card(title, children):
    return html.Div([
        html.Div(title, style={"fontSize": "13px", "fontWeight": "700", "color": "#374151",
                               "borderBottom": "2px solid #e5e7eb", "paddingBottom": "6px",
                               "marginBottom": "12px"}),
        *children,
    ], style={"background": "#fff", "borderRadius": "10px", "padding": "16px 18px",
               "boxShadow": "0 1px 6px rgba(0,0,0,0.07)", "border": "1px solid #e5e7eb",
               "marginBottom": "16px"})


def _kpi(title, value, sub="", color=BRAND):
    return html.Div([
        html.Div(title,  style={"fontSize": "11px", "fontWeight": "600", "color": "#6b7280", "textTransform": "uppercase"}),
        html.Div(value,  style={"fontSize": "24px", "fontWeight": "700", "color": color, "margin": "4px 0"}),
        html.Div(sub,    style={"fontSize": "11px", "color": "#9ca3af"}),
    ], style={"background": "#fff", "borderRadius": "10px", "padding": "14px 16px", "flex": "1",
               "minWidth": "130px", "boxShadow": "0 1px 6px rgba(0,0,0,0.07)", "border": "1px solid #e5e7eb"})


layout = html.Div([
    html.H2("Visualization", style={"marginBottom": "4px", "color": "#1f2937"}),
    html.P("Charts auto-generate from your data. Use the builder below for custom views.",
           style={"color": "#6b7280", "fontSize": "13px", "marginBottom": "20px"}),

    # ── Export strip ──────────────────────────────────────────────────────────
    html.Div([
        html.Span("Export charts: ", style={"fontSize": "13px", "color": "#6b7280",
                                              "fontWeight": "600", "marginRight": "10px"}),
        html.Button("⬇ Auto-charts PDF", id="viz-export-auto-pdf", n_clicks=0, style={
            "padding": "6px 14px", "borderRadius": "6px", "border": f"1px solid {BRAND}",
            "background": "#fff", "color": BRAND, "cursor": "pointer",
            "fontWeight": "600", "fontSize": "12px", "marginRight": "6px",
        }),
        html.Button("⬇ Custom Gallery PDF", id="viz-export-custom-pdf", n_clicks=0, style={
            "padding": "6px 14px", "borderRadius": "6px", "border": f"1px solid {BRAND}",
            "background": "#fff", "color": BRAND, "cursor": "pointer",
            "fontWeight": "600", "fontSize": "12px", "marginRight": "6px",
        }),
        html.Span(id="viz-gallery-count",
                  style={"fontSize": "11px", "color": "#9ca3af"}),
        dcc.Download(id="viz-dl-auto-pdf"),
        dcc.Download(id="viz-dl-custom-pdf"),
    ], style={"display": "flex", "alignItems": "center", "marginBottom": "16px",
               "background": "#f8fafb", "borderRadius": "8px", "padding": "10px 14px",
               "border": "1px solid #e5e7eb"}),

    # KPI strip
    dcc.Loading(
        html.Div(id="viz-kpis",
                 style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "20px"}),
        type="dot"),

    # Auto charts — stored for export
    dcc.Store(id="viz-charts-store",       storage_type="session"),
    dcc.Loading(html.Div(id="viz-auto"), type="circle"),

    # Custom builder
    html.Details([
        html.Summary(html.Span("🛠  Custom Chart Builder",
            style={"fontWeight": "700", "fontSize": "14px", "color": "#374151", "cursor": "pointer"}),
            style={"padding": "14px 0", "listStyle": "none", "userSelect": "none"}),

        html.Div([
            html.Div([
                html.Div([
                    html.Label("Chart type", style={"fontSize": "12px", "fontWeight": "600", "color": "#6b7280"}),
                    dcc.Dropdown(id="viz-type", value="bar", clearable=False, options=[
                        {"label": "Bar",       "value": "bar"},
                        {"label": "Line",      "value": "line"},
                        {"label": "Area",      "value": "area"},
                        {"label": "Scatter",   "value": "scatter"},
                        {"label": "Pie",       "value": "pie"},
                        {"label": "Pareto",    "value": "pareto"},
                        {"label": "Box",       "value": "box"},
                        {"label": "Histogram", "value": "histogram"},
                        {"label": "Heatmap",   "value": "heatmap"},
                    ]),
                ], style={"flex": "1", "minWidth": "120px"}),
                html.Div([
                    html.Label("X axis", style={"fontSize": "12px", "fontWeight": "600", "color": "#6b7280"}),
                    dcc.Dropdown(id="viz-x", placeholder="X column"),
                ], style={"flex": "1", "minWidth": "120px"}),
                html.Div([
                    html.Label("Y axis (multi-select OK)", style={"fontSize": "12px", "fontWeight": "600", "color": "#6b7280"}),
                    dcc.Dropdown(id="viz-y", placeholder="Y column(s)", multi=True),
                ], style={"flex": "1", "minWidth": "150px"}),
                html.Div([
                    html.Label("Color / Group", style={"fontSize": "12px", "fontWeight": "600", "color": "#6b7280"}),
                    dcc.Dropdown(id="viz-color", placeholder="None"),
                ], style={"flex": "1", "minWidth": "120px"}),
                html.Div([
                    html.Label("Aggregation", style={"fontSize": "12px", "fontWeight": "600", "color": "#6b7280"}),
                    dcc.Dropdown(id="viz-agg", value="sum", clearable=False, options=[
                        {"label": "Sum",   "value": "sum"},
                        {"label": "Mean",  "value": "mean"},
                        {"label": "Count", "value": "count"},
                        {"label": "Max",   "value": "max"},
                        {"label": "Min",   "value": "min"},
                    ]),
                ], style={"flex": "1", "minWidth": "100px"}),
            ], style={"display": "flex", "flexWrap": "wrap", "gap": "10px", "marginBottom": "12px"}),

            # Filter row — smart: range slider for numeric, value picker for categorical
            html.Div([
                html.Div([
                    html.Label("Filter column", style={"fontSize": "12px", "fontWeight": "600", "color": "#6b7280"}),
                    dcc.Dropdown(id="viz-fcol", placeholder="Optional"),
                ], style={"flex": "1"}),
                html.Div([
                    html.Label("Filter values / range", style={"fontSize": "12px", "fontWeight": "600", "color": "#6b7280"}),
                    # Categorical filter (shown for text columns)
                    dcc.Dropdown(id="viz-fval", multi=True, placeholder="All values"),
                    # Numeric range filter (shown for numeric columns)
                    html.Div(id="viz-frange-container", children=[
                        dcc.RangeSlider(id="viz-frange", min=0, max=100, step=1,
                                        value=[0, 100],
                                        tooltip={"placement": "bottom", "always_visible": True}),
                    ], style={"display": "none", "paddingTop": "8px"}),
                    # Date range filter (shown for date columns)
                    html.Div(id="viz-fdate-container", children=[
                        dcc.DatePickerRange(id="viz-fdate", display_format="YYYY-MM-DD",
                                            style={"fontSize": "12px"}),
                    ], style={"display": "none", "paddingTop": "8px"}),
                ], style={"flex": "2"}),
            ], style={"display": "flex", "gap": "10px", "marginBottom": "14px"}),

            html.Button("Build Chart →", id="viz-build", n_clicks=0, style={
                "padding": "8px 20px", "background": BRAND, "color": "#fff", "border": "none",
                "borderRadius": "6px", "cursor": "pointer", "fontWeight": "700", "fontSize": "13px",
            }),

            dcc.Loading(
                dcc.Graph(id="viz-custom",
                          figure={"data": [], "layout": {"title": "Configure and click Build Chart"}},
                          config=CFG, style={"marginTop": "16px"}),
                type="dot"),

            html.Div([
                html.Button("➕ Add this chart to gallery", id="viz-add-to-gallery", n_clicks=0, style={
                    "padding": "7px 16px", "borderRadius": "6px", "border": f"1px solid {BRAND}",
                    "background": "#fff", "color": BRAND, "cursor": "pointer",
                    "fontWeight": "600", "fontSize": "12px", "marginTop": "10px",
                }),
                html.Span(id="viz-add-msg", style={"fontSize": "12px", "color": "#15803d",
                                                     "marginLeft": "10px"}),
            ]),
        ], style={"padding": "0 0 16px"}),
    ], style={"background": "#fff", "borderRadius": "10px", "padding": "0 18px",
               "boxShadow": "0 1px 6px rgba(0,0,0,0.07)", "border": "1px solid #e5e7eb"}),

    # Custom gallery — every chart you've added, kept side by side
    html.Div(id="viz-gallery-section", style={"marginTop": "16px"}),
])


# ── Auto charts ───────────────────────────────────────────────────────────────

@dash.callback(
    Output("viz-kpis",        "children"),
    Output("viz-auto",        "children"),
    Output("viz-charts-store","data"),
    Input("shared-dataset",   "data"),
)
def auto_charts(shared_dataset):
    if not shared_dataset or not shared_dataset.get("records"):
        return [], html.Div("Upload data on the Ingestion page to auto-generate charts.",
                            style={"color": "#9ca3af", "padding": "40px", "textAlign": "center"}), []

    df   = _coerce(pd.DataFrame(shared_dataset["records"]))
    p    = DataProfile(df)
    num  = p.value_col
    cat  = p.group_cols[0] if p.group_cols else None
    cat2 = p.group_cols[1] if len(p.group_cols) > 1 else None
    dc   = p.date_col

    missing = int(df.isna().sum().sum())
    total_c = p.rows * p.cols_count
    kpis = [_kpi("Records", f"{p.rows:,}", f"{p.cols_count} cols")]
    kpis.append(_kpi("Complete", f"{_pct(total_c - missing, total_c)}",
                     "no gaps" if not missing else f"{missing:,} gaps",
                     color="#22c55e" if not missing else "#f59e0b"))
    if num:
        s = _series(df, num)
        kpis.append(_kpi(f"Total {num}", _fmt(s.sum()), f"avg {_fmt(s.mean())}"))
        kpis.append(_kpi(f"Peak {num}",  _fmt(s.max()), f"low {_fmt(s.min())}"))

    charts = []
    figs   = []   # kept for HTML export

    # 1. Trend over time
    if dc and num:
        tmp = df.copy()
        tmp[dc] = pd.to_datetime(tmp[dc], errors="coerce")
        tmp[num] = pd.to_numeric(tmp[num], errors="coerce")
        tmp = tmp.dropna(subset=[dc, num]).sort_values(dc)
        days = (tmp[dc].max() - tmp[dc].min()).days
        code = "Q" if days > 365 else "M" if days > 60 else "W"
        tmp["_p"] = tmp[dc].dt.to_period(code).astype(str)
        agg = tmp.groupby("_p")[num].sum().reset_index()
        agg.columns = ["Period", num]
        agg = agg.dropna(subset=[num])
        chg = _chg(agg[num].iloc[-1], agg[num].iloc[0]) if len(agg) >= 2 else ""
        fig = px.area(agg, x="Period", y=num, title=f"{num} over time  {chg}",
                      color_discrete_sequence=[BRAND])
        fig.update_traces(line_width=2.5, connectgaps=False)
        fig.update_layout(template="plotly_white", margin=dict(t=50, l=40, r=20, b=50), height=300)
        charts.append(_card(f"📈 {num} Trend", [dcc.Graph(figure=fig, config=CFG)]))
        figs.append(fig.to_json())

    # 2. Top performers
    if cat and num:
        agg = df.groupby(cat, dropna=False)[num].sum().sort_values(ascending=False).head(12).reset_index()
        grand = agg[num].sum()
        agg["pct"] = (agg[num] / grand * 100).round(1).astype(str) + "%"
        fig = px.bar(agg, x=num, y=cat, orientation="h",
                     title=f"Top {cat} by {num}",
                     text="pct", color=num,
                     color_continuous_scale=["#d1fae5", BRAND])
        fig.update_traces(textposition="outside")
        fig.update_layout(template="plotly_white", margin=dict(t=50, l=10, r=60, b=40),
                          height=320, yaxis={"categoryorder": "total ascending"},
                          coloraxis_showscale=False)
        charts.append(_card(f"🏆 Top Performers — {cat}", [dcc.Graph(figure=fig, config=CFG)]))
        figs.append(fig.to_json())

    # 3. Pareto 80/20
    if cat and num:
        agg = df.groupby(cat, dropna=False)[num].sum().sort_values(ascending=False).reset_index()
        agg.columns = [cat, num]
        total = agg[num].sum()
        agg["cum%"] = agg[num].cumsum() / total * 100 if total else 0
        fig = go.Figure()
        fig.add_trace(go.Bar(x=agg[cat], y=agg[num], name=num, marker_color=BRAND))
        fig.add_trace(go.Scatter(x=agg[cat], y=agg["cum%"], name="Cumulative %",
                                 yaxis="y2", mode="lines+markers",
                                 line=dict(color="#f59e0b", width=2.5)))
        fig.add_hline(y=80, line_dash="dot", line_color="#ef4444",
                      annotation_text="80%", yref="y2")
        fig.update_layout(
            title=f"Pareto 80/20 — {num} by {cat}",
            yaxis=dict(title=num),
            yaxis2=dict(title="Cumulative %", overlaying="y", side="right", range=[0, 108]),
            template="plotly_white", height=320,
            margin=dict(t=50, l=40, r=60, b=60),
            legend=dict(orientation="h", y=-0.2),
        )
        charts.append(_card("📊 80/20 Pareto — Where is value concentrated?", [dcc.Graph(figure=fig, config=CFG)]))
        figs.append(fig.to_json())

    # 4. Cross-category comparison
    if cat and cat2 and num:
        pivot = df.groupby([cat, cat2], dropna=False)[num].sum().reset_index()
        fig = px.bar(pivot, x=cat, y=num, color=cat2, barmode="group",
                     title=f"{num} — {cat} vs {cat2}",
                     color_discrete_sequence=px.colors.qualitative.Safe)
        fig.update_layout(template="plotly_white", height=320,
                          margin=dict(t=50, l=40, r=20, b=60))
        charts.append(_card(f"⚖️ Comparison: {cat} × {cat2}", [dcc.Graph(figure=fig, config=CFG)]))
        figs.append(fig.to_json())
    elif cat and num:
        agg = df.groupby(cat, dropna=False)[num].sum().reset_index()
        fig = px.pie(agg, names=cat, values=num, title=f"Share of {num} by {cat}",
                     color_discrete_sequence=px.colors.qualitative.Safe)
        fig.update_traces(textinfo="label+percent", textposition="outside")
        fig.update_layout(margin=dict(t=50, l=0, r=0, b=0), height=300)
        charts.append(_card(f"🥧 {cat} Market Share", [dcc.Graph(figure=fig, config=CFG)]))
        figs.append(fig.to_json())

    # 5. Revenue vs Cost vs Margin
    nums_all = p.numeric_cols
    rev_kw  = ["revenue", "sales", "income", "amount", "total", "value", "gross", "receipts"]
    cost_kw = ["cost", "expense", "cogs", "overhead", "spend", "outgoing"]
    rev_col  = next((c for kw in rev_kw  for c in nums_all if kw in c.lower()), None)
    cost_col = next((c for kw in cost_kw for c in nums_all if kw in c.lower() and c != rev_col), None)
    if rev_col and cost_col and cat:
        agg = df.groupby(cat, dropna=False).agg(
            Revenue=(rev_col, "sum"), Cost=(cost_col, "sum")
        ).reset_index()
        agg["Profit"]  = agg["Revenue"] - agg["Cost"]
        agg["Margin%"] = (agg["Profit"] / agg["Revenue"].replace(0, np.nan) * 100).round(1)
        agg = agg.sort_values("Profit", ascending=False)
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Revenue", x=agg[cat], y=agg["Revenue"], marker_color=BRAND))
        fig.add_trace(go.Bar(name="Cost",    x=agg[cat], y=agg["Cost"],    marker_color="#f87171"))
        fig.add_trace(go.Scatter(name="Margin %", x=agg[cat], y=agg["Margin%"],
                                 mode="lines+markers+text", yaxis="y2",
                                 text=agg["Margin%"].astype(str) + "%",
                                 textposition="top center",
                                 line=dict(color="#f59e0b", width=2.5)))
        fig.update_layout(
            barmode="group",
            title=f"Revenue vs Cost vs Margin by {cat}",
            yaxis=dict(title="Amount"),
            yaxis2=dict(title="Margin %", overlaying="y", side="right"),
            template="plotly_white", height=340,
            margin=dict(t=50, l=40, r=60, b=60),
            legend=dict(orientation="h", y=-0.2),
        )
        charts.append(_card("💰 Profitability: Revenue vs Cost vs Margin", [dcc.Graph(figure=fig, config=CFG)]))
        figs.append(fig.to_json())

    # 6. Correlation heatmap
    good_nums = [c for c in p.numeric_cols
                 if not (_series(df, c).is_monotonic_increasing and _series(df, c).nunique() == p.rows)]
    if len(good_nums) >= 3:
        corr = df[good_nums[:8]].corr(numeric_only=True).round(2)
        fig  = px.imshow(corr, text_auto=True, color_continuous_scale="RdYlGn",
                         zmin=-1, zmax=1,
                         title="Correlation Matrix — which numbers move together?")
        fig.update_layout(template="plotly_white", height=380,
                          margin=dict(t=50, l=10, r=10, b=10))
        charts.append(_card("🔗 Correlation Heatmap", [dcc.Graph(figure=fig, config=CFG)]))
        figs.append(fig.to_json())

    # 7. Period-over-period growth rate
    if dc and num:
        tmp = df.copy()
        tmp[dc] = pd.to_datetime(tmp[dc], errors="coerce")
        tmp[num] = pd.to_numeric(tmp[num], errors="coerce")
        tmp = tmp.dropna(subset=[dc, num]).sort_values(dc)
        days = (tmp[dc].max() - tmp[dc].min()).days
        code = "M" if days > 60 else "W"
        tmp["_p"] = tmp[dc].dt.to_period(code).astype(str)
        agg = tmp.groupby("_p")[num].sum().reset_index()
        agg.columns = ["Period", num]
        agg = agg.sort_values("Period").dropna(subset=[num])
        if len(agg) >= 3:
            agg["Growth%"] = agg[num].pct_change() * 100
            agg = agg.dropna(subset=["Growth%"])
            agg["clr"] = agg["Growth%"].apply(lambda x: "#22c55e" if x >= 0 else "#ef4444")
            fig = go.Figure(go.Bar(
                x=agg["Period"], y=agg["Growth%"],
                marker_color=agg["clr"],
                text=[f"{v:+.1f}%" for v in agg["Growth%"]],
                textposition="outside",
            ))
            fig.add_hline(y=0, line_color="#9ca3af", line_width=1)
            fig.update_layout(title=f"Period-over-Period Growth — {num} % change",
                              template="plotly_white", height=300,
                              margin=dict(t=50, l=40, r=20, b=60))
            charts.append(_card("📉📈 Growth Rate", [dcc.Graph(figure=fig, config=CFG)]))
            figs.append(fig.to_json())

    if not charts:
        return kpis, html.Div(
            "Upload data with at least one numeric column to generate charts.",
            style={"color": "#9ca3af", "padding": "30px", "textAlign": "center"}), []

    return kpis, html.Div(charts), figs


# ── Export all charts as HTML ─────────────────────────────────────────────────

@dash.callback(
    Output("viz-dl-auto-pdf", "data"),
    Input("viz-export-auto-pdf", "n_clicks"),
    State("viz-charts-store", "data"),
    prevent_initial_call=True,
)
def export_auto_pdf(_, figs_json):
    if not figs_json:
        return None
    from services.export_utils import figures_to_pdf
    pdf_bytes = figures_to_pdf(figs_json, title="DericBI Auto-Generated Charts")
    return dcc.send_bytes(lambda s: s.write(pdf_bytes), "dericbi_auto_charts.pdf")


@dash.callback(
    Output("viz-dl-custom-pdf", "data"),
    Input("viz-export-custom-pdf", "n_clicks"),
    State("viz-custom-gallery", "data"),
    prevent_initial_call=True,
)
def export_custom_pdf(_, gallery):
    if not gallery:
        return None
    from services.export_utils import figures_to_pdf
    figs_json = [item["fig_json"] for item in gallery]
    pdf_bytes = figures_to_pdf(figs_json, title="DericBI Custom Chart Gallery")
    return dcc.send_bytes(lambda s: s.write(pdf_bytes), "dericbi_custom_charts.pdf")


# ── Custom builder dropdowns ──────────────────────────────────────────────────

@dash.callback(
    Output("viz-x",     "options"),
    Output("viz-y",     "options"),
    Output("viz-color", "options"),
    Output("viz-fcol",  "options"),
    Input("shared-dataset", "data"),
)
def populate_builder(shared_dataset):
    if not shared_dataset or not shared_dataset.get("records"):
        return [], [], [], []
    df   = _coerce(pd.DataFrame(shared_dataset["records"]))
    opts = [{"label": c, "value": c} for c in df.columns]
    return opts, opts, [{"label": "None", "value": ""}] + opts, opts


# ── Smart filter: categorical → dropdown, numeric → range slider, date → date range ──

@dash.callback(
    Output("viz-fval",             "options"),
    Output("viz-fval",             "style"),
    Output("viz-frange-container", "style"),
    Output("viz-frange",           "min"),
    Output("viz-frange",           "max"),
    Output("viz-frange",           "value"),
    Output("viz-frange",           "marks"),
    Output("viz-fdate-container",  "style"),
    Output("viz-fdate",            "min_date_allowed"),
    Output("viz-fdate",            "max_date_allowed"),
    Output("viz-fdate",            "start_date"),
    Output("viz-fdate",            "end_date"),
    Input("shared-dataset", "data"),
    Input("viz-fcol",        "value"),
)
def update_filter(shared_dataset, col):
    hidden  = {"display": "none"}
    visible = {"display": "block", "paddingTop": "8px"}
    no_date = (None, None, None, None)

    if not shared_dataset or not col:
        return [], {}, hidden, 0, 100, [0, 100], {}, hidden, *no_date

    df = _coerce(pd.DataFrame(shared_dataset["records"]))
    if col not in df.columns:
        return [], {}, hidden, 0, 100, [0, 100], {}, hidden, *no_date

    series = df[col]

    # Date detection — same logic as DataProfile
    is_date = False
    if pd.api.types.is_datetime64_any_dtype(series):
        is_date = True
    elif series.dtype == object:
        parsed_check = pd.to_datetime(series, errors="coerce")
        is_date = parsed_check.notna().mean() >= 0.6

    if is_date:
        parsed = pd.to_datetime(series, errors="coerce").dropna()
        if parsed.empty:
            return [], {}, hidden, 0, 100, [0, 100], {}, hidden, *no_date
        mn_d, mx_d = parsed.min().date(), parsed.max().date()
        return [], hidden, hidden, 0, 100, [0, 100], {}, visible, mn_d, mx_d, mn_d, mx_d

    is_numeric = pd.api.types.is_numeric_dtype(series)

    if is_numeric:
        s    = pd.to_numeric(series, errors="coerce").dropna()
        mn   = float(s.min()) if not s.empty else 0
        mx   = float(s.max()) if not s.empty else 100
        marks = {
            mn: {"label": _fmt(mn)},
            mx: {"label": _fmt(mx)},
        }
        return [], hidden, visible, mn, mx, [mn, mx], marks, hidden, *no_date
    else:
        vals = sorted(series.dropna().astype(str).unique())[:200]
        opts = [{"label": v, "value": v} for v in vals]
        return opts, {}, hidden, 0, 100, [0, 100], {}, hidden, *no_date


# ── Build custom chart ────────────────────────────────────────────────────────

@dash.callback(
    Output("viz-custom", "figure"),
    Input("viz-build",   "n_clicks"),
    State("shared-dataset", "data"),
    State("viz-type",  "value"),
    State("viz-x",     "value"),
    State("viz-y",     "value"),
    State("viz-color", "value"),
    State("viz-agg",   "value"),
    State("viz-fcol",  "value"),
    State("viz-fval",  "value"),
    State("viz-frange","value"),
    State("viz-fdate", "start_date"),
    State("viz-fdate", "end_date"),
    prevent_initial_call=True,
)
def build_custom(_, shared_dataset, chart_type, x, y, color, agg, fcol, fval, frange,
                 fdate_start, fdate_end):
    if not shared_dataset or not shared_dataset.get("records"):
        return {"data": [], "layout": {"title": "No data loaded"}}

    df = _coerce(pd.DataFrame(shared_dataset["records"]))
    p  = DataProfile(df)

    # Apply filter — date range, numeric range, or categorical values
    if fcol and fcol in df.columns:
        series = df[fcol]
        is_date_col = (
            pd.api.types.is_datetime64_any_dtype(series) or
            (series.dtype == object and pd.to_datetime(series, errors="coerce").notna().mean() >= 0.6)
        )
        if is_date_col and fdate_start and fdate_end:
            parsed = pd.to_datetime(df[fcol], errors="coerce")
            df = df[(parsed >= pd.to_datetime(fdate_start)) & (parsed <= pd.to_datetime(fdate_end))]
        elif pd.api.types.is_numeric_dtype(series) and frange and len(frange) == 2:
            lo, hi = frange
            df = df[(pd.to_numeric(df[fcol], errors="coerce") >= lo) &
                    (pd.to_numeric(df[fcol], errors="coerce") <= hi)]
        elif fval:
            df = df[df[fcol].astype(str).isin(fval)]

    if df.empty:
        return {"data": [], "layout": {"title": "No rows after filter"}}

    # y is multi — normalise to list
    y_list = ([y] if isinstance(y, str) else list(y or []))
    y_list = [c for c in y_list if c and c in df.columns]
    if not y_list:
        y_list = [p.value_col] if p.value_col else (p.numeric_cols[:1] if p.numeric_cols else [])
    if not y_list:
        return {"data": [], "layout": {"title": "Select at least one Y axis column"}}

    y_primary = y_list[0]
    x = x or (p.group_cols[0] if p.group_cols else df.columns[0])
    color_use = color if color and color in df.columns else None

    # Aggregate (only when single Y — multi-Y uses raw or grouped differently)
    if x and x in df.columns and len(y_list) == 1 and agg and chart_type not in ("scatter", "box", "histogram", "heatmap"):
        num_check = pd.to_numeric(df[y_primary], errors="coerce")
        if num_check.notna().mean() >= 0.5:
            agg_map = {"sum": "sum", "mean": "mean", "count": "size", "max": "max", "min": "min"}
            fn = agg_map.get(agg, "sum")
            if fn == "size":
                df = df.groupby(x, dropna=False).size().reset_index(name="Count")
                y_primary = "Count"
                y_list = ["Count"]
            else:
                df = df.groupby(x, dropna=False)[y_primary].agg(fn).reset_index()
    elif x and x in df.columns and len(y_list) > 1 and agg and chart_type not in ("scatter", "box", "histogram", "heatmap"):
        # Multi-Y aggregate
        num_ys = [c for c in y_list if c in df.columns]
        agg_map = {"sum": "sum", "mean": "mean", "count": "size", "max": "max", "min": "min"}
        fn = agg_map.get(agg, "sum")
        df = df.groupby(x, dropna=False)[num_ys].agg(fn).reset_index()
        y_list = num_ys

    # Sort X for line/area
    if chart_type in ("line", "area") and x and x in df.columns:
        try:
            df = df.copy()
            df["__s"] = pd.to_datetime(df[x], errors="coerce")
            if df["__s"].notna().mean() >= 0.6:
                df = df.sort_values("__s").drop(columns=["__s"])
            else:
                df["__s"] = pd.to_numeric(df[x], errors="coerce")
                df = df.sort_values("__s").drop(columns=["__s"])
        except Exception:
            df = df.sort_values(x)
        drop_cols = [c for c in y_list if c in df.columns]
        if drop_cols:
            df = df.dropna(subset=drop_cols)

    try:
        title_y = " & ".join(y_list)

        if chart_type == "bar":
            if len(y_list) > 1:
                fig = px.bar(df.head(40), x=x, y=y_list, barmode="group",
                             title=f"{title_y} by {x}",
                             color_discrete_sequence=px.colors.qualitative.Safe)
            else:
                fig = px.bar(df.head(40), x=x, y=y_primary, color=color_use,
                             title=f"{y_primary} by {x}", text_auto='.2f',
                             color_discrete_sequence=px.colors.qualitative.Safe)

        elif chart_type == "line":
            if len(y_list) > 1:
                fig = px.line(df, x=x, y=y_list, markers=True,
                              title=f"{title_y} over {x}",
                              color_discrete_sequence=px.colors.qualitative.Safe)
            else:
                fig = px.line(df, x=x, y=y_primary, color=color_use,
                              title=f"{y_primary} over {x}", markers=True,
                              color_discrete_sequence=[BRAND])

        elif chart_type == "area":
            if len(y_list) > 1:
                fig = px.area(df, x=x, y=y_list,
                              title=f"{title_y} over {x}",
                              color_discrete_sequence=px.colors.qualitative.Safe)
            else:
                fig = px.area(df, x=x, y=y_primary, color=color_use,
                              title=f"{y_primary} over {x}",
                              color_discrete_sequence=[BRAND])

        elif chart_type == "scatter":
            fig = px.scatter(df, x=x, y=y_primary, color=color_use,
                             title=f"{y_primary} vs {x}",
                             color_discrete_sequence=px.colors.qualitative.Safe)

        elif chart_type == "pie":
            fig = px.pie(df.head(15), names=x, values=y_primary,
                         title=f"Share of {y_primary} by {x}",
                         color_discrete_sequence=px.colors.qualitative.Safe)

        elif chart_type == "pareto":
            raw = _coerce(pd.DataFrame(shared_dataset["records"]))
            if fcol and fcol in raw.columns and fval:
                raw = raw[raw[fcol].astype(str).isin(fval)]
            a = raw.groupby(x, dropna=False)[y_primary].sum().sort_values(ascending=False).reset_index()
            a["cum%"] = a[y_primary].cumsum() / a[y_primary].sum() * 100
            fig = go.Figure()
            fig.add_trace(go.Bar(x=a[x], y=a[y_primary], name=y_primary, marker_color=BRAND))
            fig.add_trace(go.Scatter(x=a[x], y=a["cum%"], name="Cumulative %",
                                     yaxis="y2", mode="lines+markers",
                                     line=dict(color="#f59e0b")))
            fig.add_hline(y=80, line_dash="dot", line_color="#ef4444", yref="y2")
            fig.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, 108], title="Cum %"),
                              title=f"Pareto: {y_primary} by {x}")

        elif chart_type == "box":
            orig = _coerce(pd.DataFrame(shared_dataset["records"]))
            fig = px.box(orig, x=x, y=y_primary, color=color_use,
                         title=f"Distribution of {y_primary} by {x}",
                         color_discrete_sequence=px.colors.qualitative.Safe)

        elif chart_type == "histogram":
            orig = _coerce(pd.DataFrame(shared_dataset["records"]))
            fig = px.histogram(orig, x=x or y_primary, color=color_use,
                               title=f"Distribution: {x or y_primary}",
                               color_discrete_sequence=[BRAND])

        elif chart_type == "heatmap":
            good = [c for c in p.numeric_cols
                    if not (_series(df, c).is_monotonic_increasing and _series(df, c).nunique() == p.rows)]
            corr = _coerce(pd.DataFrame(shared_dataset["records"]))[good[:8]].corr(numeric_only=True).round(2)
            fig = px.imshow(corr, text_auto=True, color_continuous_scale="RdYlGn",
                            title="Correlation Matrix")
        else:
            fig = px.scatter(title="Select a chart type")

        fig.update_layout(template="plotly_white",
                          margin=dict(t=50, l=40, r=20, b=50), height=400)
        return fig

    except Exception as e:
        return {"data": [], "layout": {"title": f"Chart error: {e}"}}


# ── Add chart to gallery (never wipes existing entries) ───────────────────────

@dash.callback(
    Output("viz-custom-gallery", "data"),
    Output("viz-add-msg",        "children"),
    Input("viz-add-to-gallery",  "n_clicks"),
    State("viz-custom",          "figure"),
    State("viz-type",            "value"),
    State("viz-x",               "value"),
    State("viz-y",               "value"),
    State("viz-custom-gallery",  "data"),
    prevent_initial_call=True,
)
def add_to_gallery(n_clicks, current_fig, chart_type, x, y, gallery):
    if not current_fig or not current_fig.get("data"):
        return dash.no_update, "⚠ Build a chart first"

    import plotly.graph_objects as go
    import uuid
    fig = go.Figure(current_fig)
    fig_json = fig.to_json()

    y_label = ", ".join(y) if isinstance(y, list) else (y or "")
    label = f"{chart_type}: {y_label} by {x}" if x else f"{chart_type}: {y_label}"

    # Work on a fresh copy — never mutate the incoming list/dicts in place.
    gallery = list(gallery) if gallery else []
    gallery.append({"id": uuid.uuid4().hex, "label": label, "fig_json": fig_json})

    return gallery, f"✓ Added — {len(gallery)} chart(s) in gallery"


# ── Render gallery — accumulates, each chart shown side by side ───────────────
# Each card/graph gets a stable id derived from its own uuid (not its list
# position), so the browser never reuses a previous chart's DOM/Plotly
# instance for a different one when the gallery grows, shrinks, or reorders.

@dash.callback(
    Output("viz-gallery-section", "children"),
    Output("viz-gallery-count",   "children"),
    Input("viz-custom-gallery",   "data"),
)
def render_gallery(gallery):
    if not gallery:
        return html.Div(), ""

    import plotly.io as pio
    cards = []
    for item in gallery:
        uid = item.get("id") or item["label"]
        fig = pio.from_json(item["fig_json"])
        cards.append(
            html.Div([
                html.Div([
                    html.Span(item["label"], style={"fontSize": "12px", "fontWeight": "600", "color": "#374151"}),
                    html.Button("✕", id={"type": "viz-remove-gallery", "uid": uid}, n_clicks=0, style={
                        "float": "right", "background": "none", "border": "none",
                        "color": "#ef4444", "cursor": "pointer", "fontWeight": "700", "fontSize": "14px",
                    }),
                ], style={"marginBottom": "6px"}),
                dcc.Graph(id={"type": "viz-gallery-graph", "uid": uid},
                          figure=fig, config=CFG, style={"height": "320px"}),
            ], id={"type": "viz-gallery-card", "uid": uid}, style={
                "background": "#fff", "borderRadius": "10px", "padding": "12px",
                "boxShadow": "0 1px 6px rgba(0,0,0,0.07)", "border": "1px solid #e5e7eb",
                "flex": "1 1 calc(50% - 8px)", "minWidth": "320px",
            })
        )

    return html.Div([
        html.Div("🖼 Your Chart Gallery", style={
            "fontSize": "15px", "fontWeight": "700", "color": "#374151", "marginBottom": "12px"
        }),
        html.Div(cards, style={"display": "flex", "flexWrap": "wrap", "gap": "16px"}),
    ]), f"{len(gallery)} chart(s) saved"


@dash.callback(
    Output("viz-custom-gallery", "data", allow_duplicate=True),
    Input({"type": "viz-remove-gallery", "uid": dash.ALL}, "n_clicks"),
    State("viz-custom-gallery", "data"),
    prevent_initial_call=True,
)
def remove_from_gallery(n_clicks_list, gallery):
    triggered = ctx.triggered_id
    if not triggered or not gallery:
        return dash.no_update
    if not any(n_clicks_list):  # initial render of new buttons fires with n_clicks=0 — ignore
        return dash.no_update
    uid = triggered["uid"]
    gallery = [g for g in gallery if (g.get("id") or g["label"]) != uid]
    return gallery
