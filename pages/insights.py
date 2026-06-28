"""
Insights — quick buttons fire immediately, loading spinner shows while working.
Uses DataProfile domain detection so language fits any dataset type.
"""
import dash
from dash import html, dcc, Input, Output, State, ctx
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from services.insights_agent import (
    generate_insight, DataProfile, _coerce, _series, _chg
)

dash.register_page(__name__, path="/insights", name="Insights")

BRAND = "#3e8865"

_QUICK = [
    ("🎯 Top actions right now",     "What are the top actions I should take?"),
    ("📊 Performance analysis",       "Show performance analysis"),
    ("📈 Trends over time",           "Show trends over time"),
    ("🔀 Segment breakdown",          "Segment breakdown"),
    ("💡 Opportunities",              "Where are the opportunities?"),
    ("⚠️ Anomalies & quality",       "Check for anomalies and data quality issues"),
    ("🔗 Correlations",               "Show correlations"),
    ("📋 Data overview",              "Give me an overview of this dataset"),
]

layout = html.Div([
    html.H2("Insights", style={"marginBottom":"4px","color":"#1f2937"}),
    html.P("Click any button for an instant answer. The system adapts to any type of data.",
           style={"color":"#6b7280","fontSize":"13px","marginBottom":"20px"}),

    # Context chart — auto from DataProfile
    dcc.Loading(
        dcc.Graph(id="ins-chart",
                  figure={"data":[],"layout":{"title":"Upload data to see your trend",
                                              "template":"plotly_white"}},
                  config={"displaylogo":False,"responsive":True},
                  style={"marginBottom":"16px"}),
        type="circle"),

    # Quick action buttons
    html.Div([
        html.Div("Click a question — answer appears instantly:",
                 style={"fontWeight":"700","fontSize":"13px","color":"#374151",
                        "marginBottom":"10px"}),
        html.Div([
            html.Button(label,
                id={"type":"ins-btn","index":i},
                n_clicks=0,
                style={
                    "margin":"4px","padding":"8px 16px","borderRadius":"20px",
                    "border":f"1px solid {BRAND}","background":"#fff","color":BRAND,
                    "cursor":"pointer","fontSize":"13px","fontWeight":"600",
                    "transition":"all 0.15s",
                })
            for i, (label,_) in enumerate(_QUICK)
        ], style={"display":"flex","flexWrap":"wrap"}),
    ], style={"background":"#f8fafb","borderRadius":"10px","padding":"16px",
               "border":"1px solid #e5e7eb","marginBottom":"16px"}),

    # Free-text
    html.Div([
        dcc.Input(
            id="ins-input", type="text", n_submit=0,
            placeholder="Or type any question — e.g. 'compare temperature by region'",
            debounce=False,
            style={"flex":"1","marginRight":"10px","padding":"9px 14px","borderRadius":"6px",
                   "border":"1px solid #d1d5db","fontSize":"13px","outline":"none"},
        ),
        html.Button("Analyse →", id="ins-run", n_clicks=0, style={
            "padding":"9px 22px","background":BRAND,"color":"#fff","border":"none",
            "borderRadius":"6px","cursor":"pointer","fontWeight":"700","fontSize":"13px",
        }),
    ], style={"display":"flex","alignItems":"center","marginBottom":"16px"}),

    # Active query display
    html.Div(id="ins-query-display", style={
        "fontSize":"12px","color":"#6b7280","marginBottom":"8px","minHeight":"18px"
    }),

    # Output with explicit loading spinner
    dcc.Loading(
        html.Div(id="ins-output", style={"minHeight":"60px"}),
        type="default",
        color=BRAND,
    ),

    # Hidden store for active query
    dcc.Store(id="ins-active-query", data=""),
])


# ── Context chart using DataProfile ───────────────────────────────────────────

@dash.callback(
    Output("ins-chart", "figure"),
    Input("shared-dataset", "data"),
)
def update_chart(shared_dataset):
    empty = {"data":[],"layout":{"title":"Upload data to see your trend","template":"plotly_white"}}
    if not shared_dataset or not shared_dataset.get("records"):
        return empty

    df = _coerce(pd.DataFrame(shared_dataset["records"]))
    p  = DataProfile(df)
    num = p.value_col
    cat = p.group_cols[0] if p.group_cols else None
    dc  = p.date_col

    try:
        if dc and num:
            tmp = df.copy()
            tmp[dc] = pd.to_datetime(tmp[dc], errors="coerce")
            tmp[num] = pd.to_numeric(tmp[num], errors="coerce")
            tmp = tmp.dropna(subset=[dc,num]).sort_values(dc)
            days = (tmp[dc].max()-tmp[dc].min()).days
            code = "Q" if days>365 else "M" if days>60 else "W"
            tmp["_p"] = tmp[dc].dt.to_period(code).astype(str)
            agg = tmp.groupby("_p")[num].sum().reset_index()
            agg.columns = ["Period", num]
            chg = _chg(agg[num].iloc[-1], agg[num].iloc[0]) if len(agg)>=2 else ""
            fig = px.area(agg, x="Period", y=num,
                          title=f"{num} over time  {chg}",
                          color_discrete_sequence=[BRAND])
            fig.update_traces(line_width=2)
        elif num and cat:
            agg = df.groupby(cat,dropna=False)[num].sum().sort_values(ascending=False).head(12).reset_index()
            fig = px.bar(agg, x=cat, y=num, title=f"{num} by {cat}",
                         color_discrete_sequence=[BRAND])
        elif num:
            fig = px.histogram(df, x=num, title=f"Distribution: {num}",
                               color_discrete_sequence=[BRAND])
        else:
            return empty

        fig.update_layout(template="plotly_white",
                          margin=dict(t=45,l=40,r=20,b=40),height=250)
        return fig
    except Exception:
        return empty


# ── Button / input → store active query ──────────────────────────────────────

@dash.callback(
    Output("ins-active-query",  "data"),
    Output("ins-input",         "value"),
    Output("ins-query-display", "children"),
    [Input({"type":"ins-btn","index":i},"n_clicks") for i in range(len(_QUICK))],
    Input("ins-run",  "n_clicks"),
    Input("ins-input","n_submit"),
    State("ins-input","value"),
    prevent_initial_call=True,
)
def set_query(*args):
    run_clicks  = args[-3]
    n_submit    = args[-2]
    input_val   = args[-1]
    triggered   = ctx.triggered_id

    if triggered == "ins-run" or triggered == "ins-input":
        q = (input_val or "").strip()
        return q, q, f"Analysing: \"{q}\"" if q else ""

    if isinstance(triggered, dict) and triggered.get("type") == "ins-btn":
        idx = triggered["index"]
        q   = _QUICK[idx][1]
        return q, q, f"Analysing: \"{q}\""

    return dash.no_update, dash.no_update, dash.no_update


# ── Active query → run insight ────────────────────────────────────────────────

@dash.callback(
    Output("ins-output", "children"),
    Input("ins-active-query", "data"),
    State("shared-dataset",   "data"),
    prevent_initial_call=True,
)
def run_insight(query, shared_dataset):
    if not query or not query.strip():
        return html.Div("Click a question above or type your own.",
                        style={"color":"#9ca3af","padding":"12px"})

    if not shared_dataset or not shared_dataset.get("records"):
        return html.Div([
            html.Span("⚠️ No data loaded. "),
            html.A("Go to Ingestion →", href="/ingestion",
                   style={"color":BRAND,"fontWeight":"600"}),
        ], style={"padding":"12px","color":"#dc2626"})

    df = pd.DataFrame(shared_dataset["records"])
    result = generate_insight(query=query.strip(), df=df)
    return _render(result)


# ── Render insight text ───────────────────────────────────────────────────────

def _render(text: str) -> html.Div:
    lines    = text.split("\n")
    children = []

    for line in lines:
        s = line.strip()
        if not s:
            children.append(html.Div(style={"height":"5px"}))
            continue

        # Section header  **...**
        if s.startswith("**") and s.endswith("**"):
            children.append(html.Div(
                s.strip("*"),
                style={"fontSize":"14px","fontWeight":"700","color":"#1f2937",
                       "marginTop":"14px","marginBottom":"5px",
                       "borderLeft":f"4px solid {BRAND}","paddingLeft":"10px"}
            ))
            continue

        # Inline **bold**
        parts = s.split("**")
        style = {
            "marginBottom":"5px","fontSize":"13.5px",
            "color":"#374151","lineHeight":"1.65",
            "paddingLeft":"12px" if len(s) > 0 and s[0] in
                "•→1234567890🎯💰📈📉📊💡⚠️🚨🔴🚀✅💎🏆🔻💲💵🔗📋" else "0",
        }
        if len(parts) > 1:
            spans = [html.Strong(p,style={"color":"#1f2937"}) if i%2==1 else p
                     for i, p in enumerate(parts)]
            children.append(html.Div(spans, style=style))
        else:
            children.append(html.Div(s, style=style))

    return html.Div(children, style={
        "background":"#fff","border":"1px solid #e5e7eb",
        "borderRadius":"10px","padding":"20px 24px",
        "boxShadow":"0 1px 6px rgba(0,0,0,0.07)",
    })
