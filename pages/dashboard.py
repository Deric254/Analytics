"""
DericBI Dashboard — the first thing a business user sees after uploading data.
Auto-detects what the data contains and immediately shows business-relevant KPIs,
trends, top performers, and health flags. Zero configuration required.
"""
import dash
from dash import html, dcc, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

dash.register_page(__name__, path="/", name="Dashboard")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _coerce(df):
    out = df.copy()
    for col in out.select_dtypes(include="object").columns:
        converted = pd.to_numeric(out[col], errors="coerce")
        if converted.notna().mean() >= 0.75:
            out[col] = converted
    return out


def _detect_dates(df):
    found = []
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            found.append(col)
        elif df[col].dtype == object:
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().mean() >= 0.6:
                found.append(col)
    return found


def _fmt(v):
    if pd.isna(v): return "N/A"
    if isinstance(v, (float, np.floating)):
        if abs(v) >= 1_000_000: return f"{v/1_000_000:,.1f}M"
        if abs(v) >= 1_000:     return f"{v:,.1f}"
        return f"{v:.2f}"
    if isinstance(v, (int, np.integer)):
        return f"{int(v):,}"
    return str(v)


def _pct(part, total):
    return f"{100*part/total:.1f}%" if total else "0%"


def _kpi_card(title, value, subtitle="", color="#3e8865"):
    return html.Div([
        html.Div(title, style={
            "fontSize": "12px", "fontWeight": "600", "color": "#6b7280",
            "textTransform": "uppercase", "letterSpacing": "0.5px", "marginBottom": "6px"
        }),
        html.Div(value, style={
            "fontSize": "28px", "fontWeight": "700", "color": color, "lineHeight": "1"
        }),
        html.Div(subtitle, style={"fontSize": "12px", "color": "#9ca3af", "marginTop": "4px"}),
    ], style={
        "background": "#fff", "borderRadius": "10px", "padding": "18px 20px",
        "boxShadow": "0 1px 6px rgba(0,0,0,0.08)", "border": "1px solid #e5e7eb",
        "flex": "1", "minWidth": "160px",
    })


def _flag_card(icon, text, color):
    return html.Div([
        html.Span(icon, style={"fontSize": "20px", "marginRight": "8px"}),
        html.Span(text, style={"fontSize": "13px"}),
    ], style={
        "background": color, "borderRadius": "8px", "padding": "10px 14px",
        "marginBottom": "6px", "display": "flex", "alignItems": "center",
    })


def _section(title, children):
    return html.Div([
        html.H4(title, style={
            "fontSize": "15px", "fontWeight": "700", "color": "#374151",
            "borderBottom": "2px solid #e5e7eb", "paddingBottom": "6px",
            "marginBottom": "14px", "marginTop": "0"
        }),
        *children,
    ], style={
        "background": "#fff", "borderRadius": "10px", "padding": "18px 20px",
        "boxShadow": "0 1px 6px rgba(0,0,0,0.08)", "border": "1px solid #e5e7eb",
        "marginBottom": "18px",
    })


# ── Main layout ───────────────────────────────────────────────────────────────

layout = html.Div([
    # Header row
    html.Div([
        html.Div([
            html.H2("Business Dashboard", style={
                "margin": "0", "fontSize": "24px", "fontWeight": "700", "color": "#1f2937"
            }),
            html.P("Upload data on the Ingestion page to auto-generate your dashboard",
                   id="dash-subtitle",
                   style={"margin": "4px 0 0", "color": "#6b7280", "fontSize": "13px"}),
        ]),
        html.Div([
            html.A(
                html.Button("→ Upload Data", style={
                    "background": "#3e8865", "color": "#fff", "border": "none",
                    "borderRadius": "6px", "padding": "8px 16px", "cursor": "pointer",
                    "fontWeight": "600", "fontSize": "13px",
                }),
                href="/ingestion"
            ),
        ]),
    ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "flex-start",
              "marginBottom": "20px"}),

    # KPI strip
    html.Div(id="dash-kpi-strip", style={"display": "flex", "gap": "14px", "flexWrap": "wrap",
                                          "marginBottom": "20px"}),

    # Health flags
    html.Div(id="dash-health-flags", style={"marginBottom": "18px"}),

    # Charts row
    html.Div([
        # Left: trend
        html.Div([
            html.Div(id="dash-trend-section"),
        ], style={"flex": "2", "minWidth": "0"}),
        # Right: top performers
        html.Div([
            html.Div(id="dash-top-section"),
        ], style={"flex": "1", "minWidth": "240px"}),
    ], style={"display": "flex", "gap": "16px", "marginBottom": "18px", "flexWrap": "wrap"}),

    # Bottom row: distribution + categorical breakdown
    html.Div([
        html.Div(id="dash-dist-section", style={"flex": "1", "minWidth": "0"}),
        html.Div(id="dash-cat-section",  style={"flex": "1", "minWidth": "0"}),
    ], style={"display": "flex", "gap": "16px", "flexWrap": "wrap"}),

    # Auto-insight summary
    html.Div(id="dash-insight-summary", style={"marginTop": "6px"}),
])


# ── Callback ──────────────────────────────────────────────────────────────────

@dash.callback(
    Output("dash-subtitle",        "children"),
    Output("dash-kpi-strip",       "children"),
    Output("dash-health-flags",    "children"),
    Output("dash-trend-section",   "children"),
    Output("dash-top-section",     "children"),
    Output("dash-dist-section",    "children"),
    Output("dash-cat-section",     "children"),
    Output("dash-insight-summary", "children"),
    Input("shared-dataset", "data"),
)
def render_dashboard(shared_dataset):
    empty_sub = "Upload data on the Ingestion page to auto-generate your dashboard."
    empty_state = (
        empty_sub, [], [], [], [], [], [],
        html.Div([
            html.Div([
                html.H3("👋 Welcome to DericBI", style={"color": "#3e8865", "marginBottom": "8px"}),
                html.P("To get started:"),
                html.Ol([
                    html.Li("Go to Ingestion → upload your CSV or Excel file"),
                    html.Li("Return here — your dashboard will auto-generate"),
                    html.Li("Use Insights for analysis, Visualization for charts, Reporting for exports"),
                ], style={"lineHeight": "2"}),
            ], style={
                "background": "#fff", "borderRadius": "10px", "padding": "30px",
                "boxShadow": "0 1px 6px rgba(0,0,0,0.08)", "border": "1px solid #e5e7eb",
            })
        ]),
    )

    if not shared_dataset or not shared_dataset.get("records"):
        return empty_state

    df = _coerce(pd.DataFrame(shared_dataset["records"]))
    filename = shared_dataset.get("filename", "your dataset")
    rows, cols = df.shape
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(exclude="number").columns.tolist()
    date_cols = _detect_dates(df)

    subtitle = f"Auto-generated from: {filename}  |  {rows:,} rows × {cols} columns"

    # ── KPI Strip ─────────────────────────────────────────────────────────────
    kpi_cards = [_kpi_card("Total Rows", f"{rows:,}", f"{cols} columns")]

    missing = int(df.isna().sum().sum())
    total_cells = rows * cols
    kpi_cards.append(_kpi_card(
        "Data Completeness",
        _pct(total_cells - missing, total_cells),
        f"{missing:,} missing cells",
        color="#22c55e" if missing == 0 else "#f59e0b",
    ))

    dups = int(df.duplicated().sum())
    kpi_cards.append(_kpi_card(
        "Unique Rows",
        f"{rows - dups:,}",
        f"{dups:,} duplicates",
        color="#22c55e" if dups == 0 else "#ef4444",
    ))

    for col in numeric_cols[:3]:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty: continue
        kpi_cards.append(_kpi_card(
            f"Total {col}", _fmt(s.sum()), f"avg {_fmt(s.mean())} / median {_fmt(s.median())}"
        ))

    # ── Health Flags ──────────────────────────────────────────────────────────
    flags = []
    if missing == 0 and dups == 0:
        flags.append(_flag_card("✅", "Dataset is clean — no missing values or duplicates", "rgba(34,197,94,0.1)"))
    if missing > 0:
        miss_pct = 100 * missing / total_cells
        flags.append(_flag_card("⚠️", f"Missing values: {missing:,} cells ({miss_pct:.1f}%) — consider cleaning on the Cleaning page", "rgba(245,158,11,0.1)"))
    if dups > 0:
        flags.append(_flag_card("🔴", f"Duplicate rows: {dups:,} ({_pct(dups, rows)}) — remove them on the Cleaning page", "rgba(239,68,68,0.1)"))

    # Outlier check on first numeric col
    if numeric_cols:
        s = pd.to_numeric(df[numeric_cols[0]], errors="coerce").dropna()
        if len(s) >= 4:
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            n_out = int(((s < q1 - 1.5*iqr) | (s > q3 + 1.5*iqr)).sum())
            if n_out:
                flags.append(_flag_card("📊", f"{n_out:,} outlier(s) in '{numeric_cols[0]}' (IQR method) — check on Insights page", "rgba(99,102,241,0.08)"))

    health_section = _section("Data Health", flags) if flags else html.Div()

    # ── Trend chart ───────────────────────────────────────────────────────────
    trend_fig = None
    trend_title = "Trend"
    if date_cols and numeric_cols:
        dc = date_cols[0]
        nc = max(numeric_cols, key=lambda c: pd.to_numeric(df[c], errors="coerce").std() or 0)
        tmp = df.copy()
        tmp[dc] = pd.to_datetime(tmp[dc], errors="coerce")
        tmp = tmp.dropna(subset=[dc, nc]).sort_values(dc)
        trend_fig = px.line(tmp, x=dc, y=nc, title=f"{nc} over time", markers=True,
                            color_discrete_sequence=["#3e8865"])
        trend_title = f"{nc} Over Time"
    elif numeric_cols:
        nc = max(numeric_cols, key=lambda c: pd.to_numeric(df[c], errors="coerce").std() or 0)
        trend_fig = px.histogram(df, x=nc, title=f"Distribution: {nc}",
                                 color_discrete_sequence=["#3e8865"])
        trend_title = f"Distribution: {nc}"

    if trend_fig:
        trend_fig.update_layout(template="plotly_white", margin=dict(t=40, l=30, r=10, b=30), height=280)
        trend_section = _section(trend_title, [dcc.Graph(figure=trend_fig, config={"displaylogo": False, "responsive": True})])
    else:
        trend_section = _section("Trend", [html.P("No date or numeric columns found.", style={"color": "#9ca3af"})])

    # ── Top performers ────────────────────────────────────────────────────────
    top_children = []
    if numeric_cols and cat_cols:
        nc = numeric_cols[0]
        # pick best groupby: skip ID-like cols (>80% unique)
        best_cat = next(
            (c for c in cat_cols if df[c].nunique() / max(len(df), 1) < 0.8 and df[c].nunique() >= 2),
            cat_cols[0]
        )
        agg = df.groupby(best_cat, dropna=False)[nc].sum().sort_values(ascending=False).head(8)
        top_fig = px.bar(
            agg.reset_index(), x=nc, y=best_cat, orientation="h",
            title=f"{nc} by {best_cat}",
            color_discrete_sequence=["#49A078"],
        )
        top_fig.update_layout(template="plotly_white", margin=dict(t=40, l=10, r=10, b=20), height=280,
                               yaxis={"categoryorder": "total ascending"})
        top_children = [dcc.Graph(figure=top_fig, config={"displaylogo": False, "responsive": True})]
    elif numeric_cols:
        top_children = [html.P("Add a categorical column to see top performers.", style={"color": "#9ca3af"})]
    else:
        top_children = [html.P("No numeric columns found.", style={"color": "#9ca3af"})]

    top_section = _section("Top Performers", top_children)

    # ── Distribution ──────────────────────────────────────────────────────────
    dist_section = html.Div()
    if len(numeric_cols) >= 2:
        dist_fig = px.box(df[numeric_cols[:4]], title="Spread of Numeric Columns",
                          color_discrete_sequence=px.colors.qualitative.Safe)
        dist_fig.update_layout(template="plotly_white", margin=dict(t=40, l=30, r=10, b=30), height=260)
        dist_section = _section("Numeric Spread", [dcc.Graph(figure=dist_fig, config={"displaylogo": False, "responsive": True})])
    elif numeric_cols:
        s = pd.to_numeric(df[numeric_cols[0]], errors="coerce").dropna()
        dist_fig = px.histogram(df, x=numeric_cols[0], color_discrete_sequence=["#3e8865"])
        dist_fig.update_layout(template="plotly_white", margin=dict(t=30, l=30, r=10, b=30), height=260)
        dist_section = _section(f"Distribution: {numeric_cols[0]}", [dcc.Graph(figure=dist_fig, config={"displaylogo": False})])

    # ── Categorical breakdown ─────────────────────────────────────────────────
    cat_section = html.Div()
    good_cats = [c for c in cat_cols if 2 <= df[c].nunique() <= 30]
    if good_cats:
        cc = good_cats[0]
        vc = df[cc].dropna().astype(str).value_counts().head(10).reset_index()
        vc.columns = [cc, "count"]
        cat_fig = px.pie(vc, names=cc, values="count", title=f"Breakdown by {cc}",
                         color_discrete_sequence=px.colors.qualitative.Safe)
        cat_fig.update_layout(margin=dict(t=40, l=0, r=0, b=0), height=260)
        cat_section = _section(f"Breakdown: {cc}", [dcc.Graph(figure=cat_fig, config={"displaylogo": False})])

    # ── Auto-insight summary ──────────────────────────────────────────────────
    insights = []

    # Highest value row
    if numeric_cols:
        nc = numeric_cols[0]
        s = pd.to_numeric(df[nc], errors="coerce")
        idx_max = s.idxmax()
        if pd.notna(idx_max):
            row = df.loc[idx_max]
            desc = " | ".join(f"{c}: {row[c]}" for c in cat_cols[:3] if c in row.index)
            insights.append(f"🏆 Highest {nc}: {_fmt(s.max())} — {desc}")

    # Trend direction
    if date_cols and numeric_cols:
        dc, nc = date_cols[0], numeric_cols[0]
        tmp = df.copy()
        tmp[dc] = pd.to_datetime(tmp[dc], errors="coerce")
        tmp = tmp.dropna(subset=[dc, nc]).sort_values(dc)
        if len(tmp) >= 4:
            n = max(len(tmp)//4, 1)
            first = pd.to_numeric(tmp[nc].iloc[:n], errors="coerce").mean()
            last  = pd.to_numeric(tmp[nc].iloc[-n:], errors="coerce").mean()
            if pd.notna(first) and pd.notna(last) and first != 0:
                chg = (last - first) / abs(first) * 100
                arrow = "📈" if chg > 0 else "📉"
                insights.append(f"{arrow} {nc} {'+' if chg > 0 else ''}{chg:.1f}% from earliest to latest records")

    # Correlation
    if len(numeric_cols) >= 2:
        corr = df[numeric_cols[:6]].corr(numeric_only=True)
        pairs = []
        cols_l = corr.columns.tolist()
        for i in range(len(cols_l)):
            for j in range(i+1, len(cols_l)):
                v = corr.iloc[i, j]
                if not pd.isna(v) and abs(v) >= 0.7:
                    pairs.append((cols_l[i], cols_l[j], v))
        if pairs:
            a, b, r = max(pairs, key=lambda x: abs(x[2]))
            insights.append(f"🔗 Strong correlation: {a} ↔ {b} (r = {r:.2f})")

    insight_items = [html.Li(i, style={"marginBottom": "6px", "fontSize": "13.5px"}) for i in insights]
    insight_section = _section("Auto-Generated Insights", [
        html.Ul(insight_items, style={"margin": "0", "paddingLeft": "20px"}) if insight_items
        else html.P("Upload data to see automated insights.", style={"color": "#9ca3af"})
    ]) if insights else html.Div()

    return (
        subtitle,
        kpi_cards,
        health_section,
        trend_section,
        top_section,
        dist_section,
        cat_section,
        insight_section,
    )
