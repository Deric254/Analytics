import dash
from dash import html, dcc, Input, Output, State
import plotly.express as px
import pandas as pd
from services.insights_agent import generate_insight as generate_llm_insight

dash.register_page(__name__, path="/insights", name="Insights")

layout = html.Div([
    html.H2("DericBI Analytics Engine - Insights", className="page-title"),

    # Chart for context
    dcc.Graph(
        id="sales-trend",
        figure={"data": [], "layout": {"title": "Upload a dataset to view trend"}}
    ),

    # User input for LLM assistant
    html.Div([
        html.Label("Ask the DericBI Assistant"),
        dcc.Input(id="insight-query", type="text", placeholder="e.g. Explain this chart"),
        html.Button("Generate Insight", id="generate-insight", n_clicks=0)
    ], style={"marginTop": "20px"}),

    # Insight Output
    html.Div(id="insight-output", style={"marginTop": "20px", "color": "green"})
])

# Placeholder callback (replace with HuggingFace API integration)
@dash.callback(
    Output("sales-trend", "figure"),
    Input("shared-dataset", "data")
)
def update_sales_trend(shared_dataset):
    if not shared_dataset or not shared_dataset.get("records"):
        return {"data": [], "layout": {"title": "Upload a dataset to view trend"}}

    df = pd.DataFrame(shared_dataset["records"])
    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    if not numeric_columns:
        return {"data": [], "layout": {"title": "No numeric columns available for trend"}}

    y_col = numeric_columns[0]
    x_candidates = df.select_dtypes(exclude="number").columns.tolist()
    x_col = x_candidates[0] if x_candidates else df.index
    return px.line(df, x=x_col, y=y_col, title=f"{y_col} Trend")

@dash.callback(
    Output("insight-output", "children"),
    Input("generate-insight", "n_clicks"),
    State("insight-query", "value"),
    State("shared-dataset", "data")
)
def generate_insight(n_clicks, query, shared_dataset):
    if n_clicks > 0 and query:
        if not shared_dataset or not shared_dataset.get("records"):
            return "Upload data first from the Ingestion page to generate insights."

        df = pd.DataFrame(shared_dataset["records"])
        return generate_llm_insight(query=query, df=df)
    return ""
