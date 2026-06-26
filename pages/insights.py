"""
Insights page — business intelligence, not statistics.
"""
import dash
from dash import html, dcc, Input, Output, State, ctx
import plotly.express as px
import pandas as pd
from services.insights_agent import generate_insight, _detect_dates, _best_num, _best_cat, _coerce

dash.register_page(__name__, path="/insights", name="Insights")

_QUICK = [
    ("🎯 What should I do now?",          "What are the top actions I should take based on this data?"),
    ("💰 Revenue performance",             "Analyse revenue performance and top earners"),
    ("📈 Trends & growth",                 "What are the trends and growth patterns over time?"),
    ("📊 Segment breakdown",               "Break down performance by segment, product or region"),
    ("💡 Growth opportunities",            "Where are the growth opportunities I'm missing?"),
    ("⚠️ Risk & concentration",            "What are the business risks and concentration issues?"),
    ("💵 Profit & margin",                 "Analyse profitability and margins"),
    ("💲 Pricing analysis",                "Analyse pricing effectiveness and gaps"),
]

layout = html.Div([
    html.H2("Business Intelligence", style={"marginBottom": "4px", "color": "#1f2937"}),
    html.P("Ask business questions — get actionable answers, not raw statistics.",
           style={"color": "#6b7280", "marginBottom": "20px", "fontSize": "13px"}),

    # Context chart
    dcc.Loading(
        dcc.Graph(
            id="insights-trend-chart",
            figure={"data": [], "layout": {"title": "Upload a dataset to see your data here",
                                            "template": "plotly_white"}},
            config={"displaylogo": False, "responsive": True},
        ),
        type="circle",
    ),

    # Quick buttons
    html.Div([
        html.P("Quick questions:", style={"fontWeight": "700", "marginBottom": "10px",
                                           "color": "#374151", "fontSize": "13px"}),
        html.Div([
            html.Button(label, id={"type": "quick-insight-btn", "index": i}, n_clicks=0,
                style={
                    "margin": "4px", "padding": "7px 14px", "borderRadius": "20px",
                    "border": "1px solid #3e8865", "background": "#fff", "color": "#3e8865",
                    "cursor": "pointer", "fontSize": "12.5px", "fontWeight": "500",
                    "transition": "background 0.15s",
                })
            for i, (label, _) in enumerate(_QUICK)
        ], style={"display": "flex", "flexWrap": "wrap"}),
    ], style={"background": "#f8fafb", "borderRadius": "10px", "padding": "16px",
               "border": "1px solid #e5e7eb", "margin": "16px 0"}),

    # Free-text input
    html.Div([
        dcc.Input(
            id="insight-query",
            type="text",
            placeholder="Or type your own question — e.g. 'which products have the worst margin?'",
            debounce=False,
            style={
                "flex": "1", "marginRight": "10px", "padding": "9px 14px",
                "borderRadius": "6px", "border": "1px solid #d1d5db",
                "fontSize": "13.5px", "outline": "none",
            },
        ),
        html.Button("Analyse →", id="generate-insight", n_clicks=0, style={
            "padding": "9px 22px", "background": "#3e8865", "color": "#fff",
            "border": "none", "borderRadius": "6px", "cursor": "pointer",
            "fontWeight": "700", "fontSize": "13.5px", "whiteSpace": "nowrap",
        }),
    ], style={"display": "flex", "alignItems": "center", "marginBottom": "16px"}),

    # Output
    dcc.Loading(
        html.Div(id="insight-output"),
        type="dot",
    ),
])


def _render_output(text: str) -> html.Div:
    lines = text.split("\n")
    children = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            children.append(html.Div(style={"height": "6px"}))
            continue

        # Section header **...**
        if stripped.startswith("**") and stripped.endswith("**"):
            children.append(html.Div(stripped.strip("*"), style={
                "fontSize": "14px", "fontWeight": "700", "color": "#1f2937",
                "marginTop": "14px", "marginBottom": "6px",
                "borderLeft": "3px solid #3e8865", "paddingLeft": "10px",
            }))
            continue

        # Icons → bullet lines
        icons = ["🎯","💰","📈","📉","📊","💡","⚠️","🚨","🔴","🚀","✅","💎","🏆","🔻","💲","💵","•","→"]
        is_bullet = any(stripped.startswith(ic) for ic in icons) or stripped.startswith("  ")

        # Inline bold
        parts = stripped.split("**")
        if len(parts) > 1:
            spans = [html.Strong(p, style={"color": "#1f2937"}) if i % 2 == 1 else p
                     for i, p in enumerate(parts)]
            children.append(html.Div(spans, style={
                "marginLeft": "12px" if is_bullet else "0",
                "marginBottom": "4px", "fontSize": "13.5px",
                "color": "#374151", "lineHeight": "1.6",
            }))
        else:
            children.append(html.Div(stripped, style={
                "marginLeft": "12px" if is_bullet else "0",
                "marginBottom": "4px", "fontSize": "13.5px",
                "color": "#374151", "lineHeight": "1.6",
            }))

    return html.Div(children, style={
        "background": "#fff", "border": "1px solid #e5e7eb",
        "borderRadius": "10px", "padding": "20px 24px",
        "boxShadow": "0 1px 6px rgba(0,0,0,0.07)",
    })


@dash.callback(
    Output("insights-trend-chart", "figure"),
    Input("shared-dataset", "data"),
)
def update_chart(shared_dataset):
    if not shared_dataset or not shared_dataset.get("records"):
        return {"data": [], "layout": {"title": "Upload a dataset to see your data here", "template": "plotly_white"}}

    df = _coerce(pd.DataFrame(shared_dataset["records"]))
    num = _best_num(df)
    cat = _best_cat(df)
    date_cols = _detect_dates(df)

    if date_cols and num:
        dc = date_cols[0]
        tmp = df.copy()
        tmp[dc] = pd.to_datetime(tmp[dc], errors="coerce")
        tmp = tmp.dropna(subset=[dc, num]).sort_values(dc)
        tmp[num] = pd.to_numeric(tmp[num], errors="coerce")

        days = (tmp[dc].max() - tmp[dc].min()).days
        if days > 365:
            tmp["period"] = tmp[dc].dt.to_period("Q").astype(str)
        elif days > 60:
            tmp["period"] = tmp[dc].dt.to_period("M").astype(str)
        else:
            tmp["period"] = tmp[dc].dt.to_period("W").astype(str)

        agg = tmp.groupby("period")[num].sum().reset_index()
        fig = px.line(agg, x="period", y=num, title=f"{num} over time",
                      markers=True, color_discrete_sequence=["#3e8865"])
        fig.update_traces(fill="tozeroy", fillcolor="rgba(62,136,101,0.08)")
    elif num and cat:
        agg = df.groupby(cat, dropna=False)[num].sum().sort_values(ascending=False).head(15).reset_index()
        fig = px.bar(agg, x=cat, y=num, title=f"{num} by {cat}",
                     color_discrete_sequence=["#3e8865"])
    elif num:
        fig = px.histogram(df, x=num, title=f"Distribution: {num}",
                           color_discrete_sequence=["#3e8865"])
    else:
        return {"data": [], "layout": {"title": "No numeric columns found", "template": "plotly_white"}}

    fig.update_layout(template="plotly_white", margin=dict(t=45, l=40, r=20, b=40), height=260)
    return fig


@dash.callback(
    Output("insight-query", "value"),
    [Input({"type": "quick-insight-btn", "index": i}, "n_clicks") for i in range(len(_QUICK))],
    prevent_initial_call=True,
)
def fill_query(*_):
    triggered = ctx.triggered_id
    if not triggered:
        return dash.no_update
    return _QUICK[triggered["index"]][1]


@dash.callback(
    Output("insight-output", "children"),
    Input("generate-insight", "n_clicks"),
    State("insight-query", "value"),
    State("shared-dataset", "data"),
    prevent_initial_call=True,
)
def run_insight(n_clicks, query, shared_dataset):
    if not n_clicks:
        return ""
    if not shared_dataset or not shared_dataset.get("records"):
        return html.Div("Upload data first from the Ingestion page.",
                        style={"color": "#dc2626", "padding": "12px"})
    if not query or not query.strip():
        return html.Div("Click a question above or type your own.",
                        style={"color": "#6b7280", "padding": "12px"})

    df = pd.DataFrame(shared_dataset["records"])
    result = generate_insight(query=query.strip(), df=df)
    return _render_output(result)
