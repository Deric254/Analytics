"""
Exploration — slice, filter, aggregate, compare. Auto-populates from DataProfile.
Results show immediately on load. Push to Visualization works.
"""
import dash
from dash import html, dcc, dash_table, Input, Output, State, ctx
import plotly.express as px
import pandas as pd
import numpy as np
from services.insights_agent import DataProfile, _coerce, _series, _fmt

dash.register_page(__name__, path="/exploration", name="Exploration")

BRAND  = "#3e8865"
CFG    = {"displaylogo": False, "responsive": True}

def _card(title, children):
    return html.Div([
        html.Div(title, style={"fontSize":"13px","fontWeight":"700","color":"#374151",
                               "borderBottom":"2px solid #e5e7eb","paddingBottom":"6px","marginBottom":"12px"}),
        *children,
    ], style={"background":"#fff","borderRadius":"10px","padding":"16px 18px",
               "boxShadow":"0 1px 6px rgba(0,0,0,0.07)","border":"1px solid #e5e7eb","marginBottom":"16px"})

def _kpi_card(title, value, sub=""):
    return html.Div([
        html.Div(title,  style={"fontSize":"11px","fontWeight":"600","color":"#6b7280","textTransform":"uppercase"}),
        html.Div(value,  style={"fontSize":"24px","fontWeight":"700","color":BRAND,"margin":"4px 0"}),
        html.Div(sub,    style={"fontSize":"11px","color":"#9ca3af"}),
    ], style={"background":"#fff","borderRadius":"10px","padding":"14px 16px","flex":"1","minWidth":"130px",
               "boxShadow":"0 1px 6px rgba(0,0,0,0.07)","border":"1px solid #e5e7eb"})

layout = html.Div([
    html.H2("Data Exploration", style={"marginBottom":"4px","color":"#1f2937"}),
    html.P("Slice, filter, aggregate and compare. Configure options and click Explore.",
           style={"color":"#6b7280","fontSize":"13px","marginBottom":"20px"}),

    html.Div([
        # ── Left panel ────────────────────────────────────────────────────────
        html.Div([
            html.Div([
                html.Label("Metric columns", style={"fontSize":"12px","fontWeight":"600","color":"#6b7280"}),
                dcc.Dropdown(id="exp-metrics", multi=True, placeholder="Numeric columns to analyse"),
            ], style={"marginBottom":"14px"}),

            html.Div([
                html.Label("Group by", style={"fontSize":"12px","fontWeight":"600","color":"#6b7280"}),
                dcc.Dropdown(id="exp-groupby", placeholder="Group results by..."),
            ], style={"marginBottom":"14px"}),

            html.Div([
                html.Label("Aggregation", style={"fontSize":"12px","fontWeight":"600","color":"#6b7280"}),
                dcc.Dropdown(id="exp-agg", value="sum", clearable=False, options=[
                    {"label":"Sum",         "value":"sum"},
                    {"label":"Average",     "value":"mean"},
                    {"label":"Count",       "value":"count"},
                    {"label":"Max",         "value":"max"},
                    {"label":"Min",         "value":"min"},
                    {"label":"Std Dev",     "value":"std"},
                    {"label":"Range",       "value":"range"},
                ]),
            ], style={"marginBottom":"14px"}),

            html.Div([
                html.Label("Rank", style={"fontSize":"12px","fontWeight":"600","color":"#6b7280"}),
                dcc.RadioItems(id="exp-rank", value="none", options=[
                    {"label":"All","value":"none"},
                    {"label":"Top N","value":"top"},
                    {"label":"Bottom N","value":"bottom"},
                ], labelStyle={"marginRight":"12px","fontSize":"13px"},
                inputStyle={"marginRight":"4px"}),
                dcc.Slider(id="exp-topn", min=3, max=50, step=1, value=10,
                           marks={3:"3",10:"10",25:"25",50:"50"},
                           tooltip={"placement":"bottom"}),
            ], style={"marginBottom":"14px"}),

            html.Hr(style={"border":"none","borderTop":"1px solid #e5e7eb","margin":"8px 0"}),
            html.Div("Filters", style={"fontSize":"12px","fontWeight":"700","color":"#6b7280",
                                       "marginBottom":"10px","textTransform":"uppercase"}),

            html.Div([
                html.Label("Filter column 1", style={"fontSize":"12px","fontWeight":"600","color":"#6b7280"}),
                dcc.Dropdown(id="exp-f1-col", placeholder="Column..."),
                dcc.Dropdown(id="exp-f1-val", multi=True, placeholder="Values...",
                             style={"marginTop":"4px"}),
            ], style={"marginBottom":"12px"}),

            html.Div([
                html.Label("Filter column 2", style={"fontSize":"12px","fontWeight":"600","color":"#6b7280"}),
                dcc.Dropdown(id="exp-f2-col", placeholder="Column..."),
                dcc.Dropdown(id="exp-f2-val", multi=True, placeholder="Values...",
                             style={"marginTop":"4px"}),
            ], style={"marginBottom":"16px"}),

            html.Div([
                html.Button("Explore →", id="exp-apply", n_clicks=0, style={
                    "padding":"9px 20px","background":BRAND,"color":"#fff","border":"none",
                    "borderRadius":"6px","cursor":"pointer","fontWeight":"700","fontSize":"13px",
                    "marginRight":"8px",
                }),
                html.Button("Push to Visualization", id="exp-push", n_clicks=0, style={
                    "padding":"9px 14px","background":"#fff","color":BRAND,
                    "border":f"1px solid {BRAND}","borderRadius":"6px",
                    "cursor":"pointer","fontWeight":"600","fontSize":"12px",
                }),
            ]),
            dcc.Store(id="shared-visual-config", storage_type="session"),
        ], style={"width":"250px","flexShrink":"0","background":"#fff","borderRadius":"10px",
                  "padding":"18px","boxShadow":"0 1px 6px rgba(0,0,0,0.07)",
                  "border":"1px solid #e5e7eb","alignSelf":"flex-start"}),

        # ── Right panel ───────────────────────────────────────────────────────
        html.Div([
            html.Div(id="exp-message", style={"marginBottom":"12px","fontSize":"13px"}),
            dcc.Loading(
                html.Div(id="exp-kpis",
                         style={"display":"flex","gap":"12px","flexWrap":"wrap","marginBottom":"16px"}),
                type="dot"),
            dcc.Loading(
                dcc.Graph(id="exp-chart",
                          figure={"data":[],"layout":{"title":"Configure options and click Explore"}},
                          config=CFG),
                type="circle"),
            dcc.Loading(html.Div(id="exp-table", style={"marginTop":"14px"}), type="dot"),
        ], style={"flex":"1","minWidth":"0"}),
    ], style={"display":"flex","gap":"16px","alignItems":"flex-start"}),
])


# ── Populate dropdowns from DataProfile ───────────────────────────────────────

@dash.callback(
    Output("exp-metrics", "options"),
    Output("exp-metrics", "value"),
    Output("exp-groupby", "options"),
    Output("exp-groupby", "value"),
    Output("exp-f1-col",  "options"),
    Output("exp-f2-col",  "options"),
    Input("shared-dataset", "data"),
)
def populate_dropdowns(shared_dataset):
    if not shared_dataset or not shared_dataset.get("records"):
        return [], [], [], None, [], []
    df   = _coerce(pd.DataFrame(shared_dataset["records"]))
    p    = DataProfile(df)
    nums = [{"label": c, "value": c} for c in p.numeric_cols]
    all_cols = [{"label": c, "value": c} for c in df.columns]
    # Smart defaults from DataProfile
    default_metrics = [p.value_col] if p.value_col else p.numeric_cols[:2]
    default_group   = p.group_cols[0] if p.group_cols else None
    return nums, default_metrics, all_cols, default_group, all_cols, all_cols


@dash.callback(
    Output("exp-f1-val", "options"),
    Input("shared-dataset", "data"),
    Input("exp-f1-col",    "value"),
)
def f1_values(shared_dataset, col):
    if not shared_dataset or not col: return []
    df = pd.DataFrame(shared_dataset["records"])
    if col not in df.columns: return []
    vals = sorted(df[col].dropna().astype(str).unique())[:300]
    return [{"label": v, "value": v} for v in vals]


@dash.callback(
    Output("exp-f2-val", "options"),
    Input("shared-dataset", "data"),
    Input("exp-f2-col",    "value"),
)
def f2_values(shared_dataset, col):
    if not shared_dataset or not col: return []
    df = pd.DataFrame(shared_dataset["records"])
    if col not in df.columns: return []
    vals = sorted(df[col].dropna().astype(str).unique())[:300]
    return [{"label": v, "value": v} for v in vals]


# ── Main exploration callback ─────────────────────────────────────────────────

def _agg_series(s: pd.Series, agg: str):
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty: return np.nan
    if agg == "sum":   return s.sum()
    if agg == "mean":  return s.mean()
    if agg == "count": return s.count()
    if agg == "max":   return s.max()
    if agg == "min":   return s.min()
    if agg == "std":   return s.std()
    if agg == "range": return s.max() - s.min()
    return s.mean()


@dash.callback(
    Output("exp-message", "children"),
    Output("exp-kpis",    "children"),
    Output("exp-chart",   "figure"),
    Output("exp-table",   "children"),
    Input("exp-apply",    "n_clicks"),
    State("shared-dataset","data"),
    State("exp-metrics",  "value"),
    State("exp-groupby",  "value"),
    State("exp-agg",      "value"),
    State("exp-rank",     "value"),
    State("exp-topn",     "value"),
    State("exp-f1-col",   "value"),
    State("exp-f1-val",   "value"),
    State("exp-f2-col",   "value"),
    State("exp-f2-val",   "value"),
    prevent_initial_call=True,
)
def run_exploration(_, shared_dataset, metrics, groupby, agg, rank, topn,
                    f1_col, f1_val, f2_col, f2_val):
    if not shared_dataset or not shared_dataset.get("records"):
        return "No data loaded — go to Ingestion first.", [], \
               {"data":[],"layout":{"title":"No data"}}, html.Div()

    df = _coerce(pd.DataFrame(shared_dataset["records"]))
    p  = DataProfile(df)

    # Apply filters
    if f1_col and f1_col in df.columns and f1_val:
        df = df[df[f1_col].astype(str).isin(f1_val)]
    if f2_col and f2_col in df.columns and f2_val:
        df = df[df[f2_col].astype(str).isin(f2_val)]

    if df.empty:
        return "No rows after filters.", [], {"data":[],"layout":{"title":"No rows after filter"}}, html.Div()

    # Default metrics from DataProfile if none selected
    metrics = metrics or ([p.value_col] if p.value_col else p.numeric_cols[:2])
    metrics = [c for c in (metrics or []) if c in df.columns]

    # ── KPI strip ─────────────────────────────────────────────────────────────
    kpi_cards = [_kpi_card("Rows", f"{len(df):,}", "after filters")]
    for m in metrics[:4]:
        val = _agg_series(df[m], agg)
        kpi_cards.append(_kpi_card(f"{agg.title()} {m}", _fmt(val)))

    # ── Grouped result ────────────────────────────────────────────────────────
    if groupby and groupby in df.columns and metrics:
        def agg_fn(x): return _agg_series(x, agg)
        result = df.groupby(groupby, dropna=False)[metrics].agg(agg_fn).reset_index()
        sort_col = metrics[0]

        if rank == "top":
            result = result.sort_values(sort_col, ascending=False).head(topn)
        elif rank == "bottom":
            result = result.sort_values(sort_col, ascending=True).head(topn)
        else:
            result = result.sort_values(sort_col, ascending=False)

        # Chart
        if len(metrics) == 1:
            fig = px.bar(result.head(30), x=groupby, y=sort_col,
                         title=f"{agg.title()} of {sort_col} by {groupby}",
                         color=sort_col,
                         color_continuous_scale=["#d1fae5", BRAND],
                         text_auto=True)
            fig.update_layout(coloraxis_showscale=False)
        else:
            fig = px.bar(result.head(30), x=groupby, y=metrics, barmode="group",
                         title=f"{agg.title()} by {groupby}",
                         color_discrete_sequence=px.colors.qualitative.Safe)

        fig.update_layout(template="plotly_white",
                          margin=dict(t=50,l=40,r=20,b=60), height=360)
        table_df = result

    elif metrics:
        # No groupby — summary stats
        rows = []
        for m in metrics:
            s = pd.to_numeric(df[m], errors="coerce").dropna()
            rows.append({
                "Column": m,
                "Count":  f"{len(s):,}",
                "Sum":    _fmt(s.sum()),
                "Mean":   _fmt(s.mean()),
                "Median": _fmt(s.median()),
                "Std":    _fmt(s.std()),
                "Min":    _fmt(s.min()),
                "Max":    _fmt(s.max()),
            })
        table_df = pd.DataFrame(rows)
        fig = px.box(df[metrics], title="Distribution of selected metrics",
                     color_discrete_sequence=px.colors.qualitative.Safe)
        fig.update_layout(template="plotly_white",
                          margin=dict(t=50,l=40,r=20,b=40), height=340)
    else:
        return "Select at least one metric.", kpi_cards, \
               {"data":[],"layout":{"title":"Select metrics"}}, html.Div()

    # Table
    table = dash_table.DataTable(
        data=table_df.head(100).to_dict("records"),
        columns=[{"name": c, "id": c} for c in table_df.columns],
        style_table={"overflowX":"auto"},
        style_header={"background":"#f3f4f6","fontWeight":"700","fontSize":"12px","border":"none"},
        style_cell={"fontSize":"12px","padding":"7px 10px"},
        style_data_conditional=[{"if":{"row_index":"odd"},"backgroundColor":"#fafafa"}],
        page_size=20,
        export_format="csv",
    )

    msg = (f"✓  {len(df):,} rows  |  {agg} of {', '.join(metrics)}"
           + (f"  grouped by {groupby}" if groupby else ""))

    return (html.Span(msg, style={"color":"#15803d","fontWeight":"600"}),
            kpi_cards, fig, table)


@dash.callback(
    Output("shared-visual-config", "data"),
    Input("exp-push",  "n_clicks"),
    State("exp-groupby","value"),
    State("exp-metrics","value"),
    State("exp-agg",    "value"),
    prevent_initial_call=True,
)
def push_to_viz(_, groupby, metrics, agg):
    metrics = metrics or []
    return {"x": groupby, "y": metrics[0] if metrics else None, "aggregation": agg, "chart_type": "bar"}
