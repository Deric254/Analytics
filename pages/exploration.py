import dash
from dash import html, dcc, dash_table, Input, Output, State
import pandas as pd
import plotly.express as px
from services.export_utils import format_compact_number

dash.register_page(__name__, path="/exploration", name="Exploration & Modeling")

layout = html.Div([
    html.H2("DericBI Analytics Engine - Exploration & Modeling", className="page-title"),

    html.Div([
        html.Label("Aggregation"),
        dcc.Dropdown(
            id="exp-aggregation",
            options=[
                {"label": "Sum", "value": "sum"},
                {"label": "Average", "value": "mean"},
                {"label": "Minimum", "value": "min"},
                {"label": "Maximum", "value": "max"},
                {"label": "Range (max-min)", "value": "range"},
                {"label": "Count", "value": "count"},
            ],
            value="mean",
            placeholder="Choose aggregation method"
        ),
        html.Label("Metric columns"),
        dcc.Dropdown(id="exp-metrics", multi=True, placeholder="Choose one or more numeric metrics"),
        html.Label("Group by"),
        dcc.Dropdown(id="exp-groupby", placeholder="Optional: group results by a column"),
        html.Label("Top/Bottom ranking"),
        dcc.RadioItems(
            id="exp-rank-mode",
            options=[
                {"label": "None", "value": "none"},
                {"label": "Top", "value": "top"},
                {"label": "Bottom", "value": "bottom"},
            ],
            value="none"
        ),
        dcc.Slider(id="exp-topn", min=3, max=100, step=1, value=10),
        html.Label("Number format"),
        dcc.Dropdown(
            id="exp-number-format",
            options=[
                {"label": "Plain", "value": "plain"},
                {"label": "K", "value": "k"},
                {"label": "M", "value": "m"},
                {"label": "B", "value": "b"},
                {"label": "Currency", "value": "currency"},
            ],
            value="plain",
            placeholder="Choose number format"
        ),
        html.Label("Currency (for currency format)"),
        dcc.Dropdown(
            id="exp-currency",
            options=[
                {"label": "USD", "value": "USD"},
                {"label": "EUR", "value": "EUR"},
                {"label": "GBP", "value": "GBP"},
                {"label": "KES", "value": "KES"},
                {"label": "INR", "value": "INR"},
                {"label": "JPY", "value": "JPY"},
            ],
            value="USD",
            placeholder="Select currency"
        ),
        html.Label("Slicer 1 column"),
        dcc.Dropdown(id="exp-slicer1-column", placeholder="Choose first slicer column"),
        dcc.Dropdown(id="exp-slicer1-values", multi=True, placeholder="Choose first slicer values"),
        html.Label("Slicer 2 column"),
        dcc.Dropdown(id="exp-slicer2-column", placeholder="Choose second slicer column"),
        dcc.Dropdown(id="exp-slicer2-values", multi=True, placeholder="Choose second slicer values"),
        html.Label("Preferred chart type for push to Visualization"),
        dcc.Dropdown(
            id="exp-chart-type",
            options=[
                {"label": "Bar", "value": "bar"},
                {"label": "Line", "value": "line"},
                {"label": "Scatter", "value": "scatter"},
                {"label": "Histogram", "value": "histogram"},
                {"label": "Box", "value": "box"},
                {"label": "Pie", "value": "pie"},
            ],
            value="bar",
            placeholder="Select chart type to push"
        ),
        html.Button("Apply Exploration", id="exp-apply", n_clicks=0, style={"marginTop": "10px"}),
        html.Button("Push to Visualization", id="exp-push", n_clicks=0, style={"marginTop": "10px", "marginLeft": "8px"}),
    ], style={"marginTop": "20px"}),

    html.Div(id="exploration-message", style={"marginTop": "10px"}),
    html.Div(id="exploration-kpis", className="kpi-container", style={"marginTop": "20px"}),
    dcc.Graph(id="exploration-preview-chart"),
    html.Div(id="exploration-content", style={"marginTop": "20px"})
])


def _safe_aggregate(series: pd.Series, agg: str):
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if agg == "sum":
        return clean.sum()
    if agg == "mean":
        return clean.mean()
    if agg == "min":
        return clean.min()
    if agg == "max":
        return clean.max()
    if agg == "range":
        return clean.max() - clean.min() if not clean.empty else float("nan")
    if agg == "count":
        return clean.count()
    return clean.mean()


@dash.callback(
    Output("exp-metrics", "options"),
    Output("exp-metrics", "value"),
    Output("exp-groupby", "options"),
    Output("exp-groupby", "value"),
    Output("exp-slicer1-column", "options"),
    Output("exp-slicer2-column", "options"),
    Input("shared-dataset", "data")
)
def update_exploration_options(shared_dataset):
    if not shared_dataset or not shared_dataset.get("records"):
        return [], [], [], None, [], []

    df = pd.DataFrame(shared_dataset["records"])
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    all_cols = df.columns.tolist()

    metric_options = [{"label": c, "value": c} for c in numeric_cols]
    group_options = [{"label": c, "value": c} for c in all_cols]
    default_metrics = numeric_cols[:2] if len(numeric_cols) >= 2 else numeric_cols

    return metric_options, default_metrics, group_options, (all_cols[0] if all_cols else None), group_options, group_options


@dash.callback(
    Output("exp-slicer1-values", "options"),
    Output("exp-slicer2-values", "options"),
    Input("shared-dataset", "data"),
    Input("exp-slicer1-column", "value"),
    Input("exp-slicer2-column", "value")
)
def update_slicer_values(shared_dataset, slicer1_col, slicer2_col):
    if not shared_dataset or not shared_dataset.get("records"):
        return [], []

    df = pd.DataFrame(shared_dataset["records"])

    def options_for(column):
        if not column or column not in df.columns:
            return []
        vals = df[column].dropna().astype(str).unique().tolist()
        vals = sorted(vals)[:500]
        return [{"label": v, "value": v} for v in vals]

    return options_for(slicer1_col), options_for(slicer2_col)


@dash.callback(
    Output("exploration-message", "children"),
    Output("exploration-kpis", "children"),
    Output("exploration-preview-chart", "figure"),
    Output("exploration-content", "children"),
    Input("exp-apply", "n_clicks"),
    Input("shared-dataset", "data"),
    State("exp-aggregation", "value"),
    State("exp-metrics", "value"),
    State("exp-groupby", "value"),
    State("exp-rank-mode", "value"),
    State("exp-topn", "value"),
    State("exp-number-format", "value"),
    State("exp-currency", "value"),
    State("exp-slicer1-column", "value"),
    State("exp-slicer1-values", "value"),
    State("exp-slicer2-column", "value"),
    State("exp-slicer2-values", "value"),
)
def render_exploration(n_clicks, shared_dataset, aggregation, metrics, groupby_col, rank_mode, topn,
                       number_format, currency, slicer1_col, slicer1_values, slicer2_col, slicer2_values):
    if not shared_dataset or not shared_dataset.get("records"):
        return "No uploaded data found. Upload from Ingestion first.", [], px.scatter(title="Upload data first"), html.Div("No data")

    df = pd.DataFrame(shared_dataset["records"])

    if df.empty:
        return "Uploaded dataset is empty.", [], px.scatter(title="Empty dataset"), html.Div("No data")

    filtered_df = df.copy()
    if slicer1_col and slicer1_col in filtered_df.columns and slicer1_values:
        filtered_df = filtered_df[filtered_df[slicer1_col].astype(str).isin([str(v) for v in slicer1_values])]
    if slicer2_col and slicer2_col in filtered_df.columns and slicer2_values:
        filtered_df = filtered_df[filtered_df[slicer2_col].astype(str).isin([str(v) for v in slicer2_values])]

    if filtered_df.empty:
        return "Slicers returned no rows.", [], px.scatter(title="No rows after filtering"), html.Div("No rows after filters")

    metrics = metrics or filtered_df.select_dtypes(include="number").columns.tolist()[:2]
    valid_metrics = [col for col in metrics if col in filtered_df.columns]
    if not valid_metrics and aggregation != "count":
        return "Pick at least one numeric metric.", [], px.scatter(title="Select numeric metrics"), html.Div("No numeric metric selected")

    kpis = []
    for metric in valid_metrics:
        value = _safe_aggregate(filtered_df[metric], aggregation)
        kpis.append(
            html.Div([
                html.H3(f"{aggregation.upper()} {metric}"),
                html.P(format_compact_number(value, number_format=number_format, currency=currency), className="kpi-value"),
            ], className="kpi-card")
        )

    if aggregation == "count" and not valid_metrics:
        total = len(filtered_df)
        kpis.append(
            html.Div([
                html.H3("COUNT"),
                html.P(f"{total:,}", className="kpi-value"),
            ], className="kpi-card")
        )

    if groupby_col and groupby_col in filtered_df.columns:
        grouped = filtered_df.groupby(groupby_col, dropna=False)
        if aggregation == "count":
            result = grouped.size().reset_index(name="count")
            sort_col = "count"
        else:
            result = grouped[valid_metrics].agg(
                (lambda x: _safe_aggregate(x, aggregation))
            ).reset_index()
            sort_col = valid_metrics[0]

        if rank_mode == "top":
            result = result.sort_values(by=sort_col, ascending=False).head(topn)
        elif rank_mode == "bottom":
            result = result.sort_values(by=sort_col, ascending=True).head(topn)

        preview_y = sort_col
        preview_fig = px.bar(result, x=groupby_col, y=preview_y, title=f"{aggregation.upper()} by {groupby_col}")
        table_df = result
    else:
        rows = []
        for metric in valid_metrics:
            rows.append({"metric": metric, "aggregation": aggregation, "value": _safe_aggregate(filtered_df[metric], aggregation)})
        if aggregation == "count" and not rows:
            rows.append({"metric": "rows", "aggregation": "count", "value": len(filtered_df)})

        table_df = pd.DataFrame(rows)
        if not valid_metrics:
            preview_fig = px.histogram(filtered_df, x=filtered_df.columns[0], title="Distribution preview")
        else:
            preview_fig = px.histogram(filtered_df, x=valid_metrics[0], title=f"Distribution: {valid_metrics[0]}")

    table = dash_table.DataTable(
        data=table_df.to_dict("records"),
        columns=[{"name": i, "id": i} for i in table_df.columns],
        page_size=15,
        style_table={"overflowX": "auto"}
    )

    message = f"Exploration ready. Rows after slicers: {len(filtered_df):,}. Columns: {len(filtered_df.columns)}"

    return message, kpis, preview_fig, table


@dash.callback(
    Output("shared-visual-config", "data"),
    Input("exp-push", "n_clicks"),
    State("exp-chart-type", "value"),
    State("exp-groupby", "value"),
    State("exp-metrics", "value"),
    State("exp-aggregation", "value"),
    prevent_initial_call=True
)
def push_to_visualization(n_clicks, chart_type, groupby_col, metrics, aggregation):
    metrics = metrics or []
    return {
        "chart_type": chart_type,
        "x": groupby_col,
        "y": metrics[0] if metrics else None,
        "aggregation": aggregation,
    }
