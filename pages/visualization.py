import dash
from dash import html, dcc, Input, Output, State, ctx
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from services.export_utils import format_compact_number, visuals_to_html, visuals_to_pdf_bytes, figures_to_zip_bytes


COLOR_PALETTES = {
    "plotly": px.colors.qualitative.Plotly,
    "safe": px.colors.qualitative.Safe,
    "vivid": px.colors.qualitative.Vivid,
    "bold": px.colors.qualitative.Bold,
    "pastel": px.colors.qualitative.Pastel,
    "dark24": px.colors.qualitative.Dark24,
}

INTERACTIVE_GRAPH_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "scrollZoom": True,
    "editable": True,
    "edits": {
        "titleText": True,
        "axisTitleText": True,
        "legendText": True,
        "annotationText": True,
        "shapePosition": True,
    },
    "toImageButtonOptions": {"format": "png", "filename": "dericbi_visual", "scale": 2},
}

dash.register_page(__name__, path="/visualization", name="Visualization & KPIs")

layout = html.Div([
    html.H2("DericBI Analytics Engine - Visualization & KPIs", className="page-title"),
    dcc.Store(id="viz-kpi-definitions", storage_type="session", data=[]),
    dcc.Store(id="viz-figure-store", storage_type="session", data=[]),
    dcc.Store(id="viz-user-charts", storage_type="session", data=[]),

    html.Div([
        html.H4("Slicers"),
        html.Label("Slicer 1 column"),
        dcc.Dropdown(id="viz-slicer1-column", placeholder="Choose first slicer column"),
        dcc.Dropdown(id="viz-slicer1-values", multi=True, placeholder="Choose first slicer values"),
        html.Label("Slicer 2 column"),
        dcc.Dropdown(id="viz-slicer2-column", placeholder="Choose second slicer column"),
        dcc.Dropdown(id="viz-slicer2-values", multi=True, placeholder="Choose second slicer values"),
    ], style={"marginBottom": "20px"}),

    html.Div([
        html.H4("Chart Builder"),
        html.Label("Chart type"),
        dcc.Dropdown(
            id="viz-chart-type",
            options=[
                {"label": "Bar", "value": "bar"},
                {"label": "Line", "value": "line"},
                {"label": "Scatter", "value": "scatter"},
                {"label": "Histogram", "value": "histogram"},
                {"label": "Box", "value": "box"},
                {"label": "Violin", "value": "violin"},
                {"label": "Pie", "value": "pie"},
                {"label": "Pareto", "value": "pareto"},
                {"label": "Heatmap (numeric correlation)", "value": "heatmap"}
            ],
            value="bar",
            placeholder="Select chart type"
        ),
        html.Label("X column"),
        dcc.Dropdown(id="viz-x", placeholder="Select X-axis column"),
        html.Label("Y column"),
        dcc.Dropdown(id="viz-y", placeholder="Select Y-axis column"),
        html.Label("Color column (optional)"),
        dcc.Dropdown(id="viz-color", placeholder="Optional: color grouping column"),
        html.Label("Size column (optional, scatter only)"),
        dcc.Dropdown(id="viz-size", placeholder="Optional: bubble size numeric column"),
        html.Label("Aggregation"),
        dcc.Dropdown(
            id="viz-aggregation",
            options=[
                {"label": "None", "value": "none"},
                {"label": "Count", "value": "count"},
                {"label": "Sum", "value": "sum"},
                {"label": "Mean", "value": "mean"},
                {"label": "Min", "value": "min"},
                {"label": "Max", "value": "max"}
            ],
            value="none",
            placeholder="Select aggregation"
        ),
        html.Label("Chart title"),
        dcc.Input(id="viz-title", type="text", placeholder="Custom chart title (optional)", style={"width": "100%"}),
        html.Div([
            html.Div([
                html.Label("X-axis label"),
                dcc.Input(id="viz-x-label", type="text", placeholder="Custom X label", style={"width": "100%"}),
            ], style={"flex": "1", "marginRight": "8px"}),
            html.Div([
                html.Label("Y-axis label"),
                dcc.Input(id="viz-y-label", type="text", placeholder="Custom Y label", style={"width": "100%"}),
            ], style={"flex": "1"}),
        ], style={"display": "flex", "marginTop": "8px"}),
        html.Label("Theme", style={"marginTop": "8px"}),
        dcc.Dropdown(
            id="viz-theme",
            options=[
                {"label": "Clean White", "value": "plotly_white"},
                {"label": "Simple White", "value": "simple_white"},
                {"label": "Professional Gray", "value": "seaborn"},
                {"label": "Soft Grid", "value": "ggplot2"},
                {"label": "Dark", "value": "plotly_dark"},
            ],
            value="plotly_white",
            clearable=False,
        ),
        html.Label("Color palette", style={"marginTop": "8px"}),
        dcc.Dropdown(
            id="viz-palette",
            options=[
                {"label": "Plotly", "value": "plotly"},
                {"label": "Safe", "value": "safe"},
                {"label": "Vivid", "value": "vivid"},
                {"label": "Bold", "value": "bold"},
                {"label": "Pastel", "value": "pastel"},
                {"label": "Dark24", "value": "dark24"},
            ],
            value="plotly",
            clearable=False,
        ),
        html.Label("Value label format", style={"marginTop": "8px"}),
        dcc.Dropdown(
            id="viz-value-format",
            options=[
                {"label": "Plain", "value": "plain"},
                {"label": "K", "value": "k"},
                {"label": "M", "value": "m"},
                {"label": "B", "value": "b"},
                {"label": "Currency", "value": "currency"},
                {"label": "Percent", "value": "percent"},
            ],
            value="plain",
            clearable=False,
        ),
        html.Label("Currency (if Currency format)"),
        dcc.Dropdown(
            id="viz-value-currency",
            options=[
                {"label": "USD", "value": "USD"},
                {"label": "EUR", "value": "EUR"},
                {"label": "GBP", "value": "GBP"},
                {"label": "KES", "value": "KES"},
                {"label": "INR", "value": "INR"},
                {"label": "JPY", "value": "JPY"},
            ],
            value="USD",
            clearable=False,
        ),
        dcc.Checklist(
            id="viz-style-options",
            options=[
                {"label": "Show data labels", "value": "labels"},
                {"label": "Convert bars/lines/histograms to %", "value": "percent"},
                {"label": "Show legend", "value": "legend"},
            ],
            value=["legend"],
            style={"marginTop": "8px"}
        ),
        html.Label("Max categories/bars", style={"marginTop": "8px"}),
        dcc.Slider(id="viz-max-bars", min=3, max=12, step=1, value=6),
        html.Label("High-cardinality handling"),
        dcc.Dropdown(
            id="viz-category-reduction",
            options=[
                {"label": "Numeric bands (best for payments)", "value": "bins"},
                {"label": "Top categories + Other", "value": "top_other"},
            ],
            value="bins",
            clearable=False,
        ),
        dcc.Checklist(
            id="viz-auto-toggle",
            options=[{"label": "Generate visuals for all columns", "value": "auto"}],
            value=["auto"]
        ),
    ], style={"marginBottom": "20px"}),

    html.Div([
        html.H4("KPI Builder"),
        html.Label("KPI column"),
        dcc.Dropdown(id="viz-kpi-column", placeholder="Choose numeric column for KPI"),
        html.Label("KPI operation"),
        dcc.Dropdown(
            id="viz-kpi-operation",
            options=[
                {"label": "Sum", "value": "sum"},
                {"label": "Average", "value": "mean"},
                {"label": "Minimum", "value": "min"},
                {"label": "Maximum", "value": "max"},
                {"label": "Range (max-min)", "value": "range"},
                {"label": "Count", "value": "count"},
                {"label": "Top N Sum", "value": "top"},
                {"label": "Bottom N Sum", "value": "bottom"},
            ],
            value="sum",
            placeholder="Choose KPI operation"
        ),
        html.Label("N for Top/Bottom"),
        dcc.Slider(id="viz-kpi-n", min=1, max=100, step=1, value=5),
        html.Label("Number format"),
        dcc.Dropdown(
            id="viz-kpi-format",
            options=[
                {"label": "Plain", "value": "plain"},
                {"label": "K", "value": "k"},
                {"label": "M", "value": "m"},
                {"label": "B", "value": "b"},
                {"label": "Currency", "value": "currency"},
            ],
            value="plain",
            placeholder="Select number display format"
        ),
        html.Label("Currency"),
        dcc.Dropdown(
            id="viz-kpi-currency",
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
        html.Button("Add KPI", id="viz-add-kpi", n_clicks=0, style={"marginTop": "8px"}),
        html.Button("Clear KPIs", id="viz-clear-kpi", n_clicks=0, style={"marginTop": "8px", "marginLeft": "8px"}),
    ], style={"marginBottom": "20px"}),

    html.Div([
        html.Button("Export Visuals HTML", id="export-visuals-html", n_clicks=0),
        html.Button("Export Visuals PDF", id="export-visuals-pdf", n_clicks=0, style={"marginLeft": "8px"}),
        html.Button("Export Visuals ZIP", id="export-visuals-zip", n_clicks=0, style={"marginLeft": "8px"}),
        dcc.Download(id="visuals-html-download"),
        dcc.Download(id="visuals-pdf-download"),
        dcc.Download(id="visuals-zip-download"),
    ], style={"marginBottom": "20px"}),

    html.Div(id="visualization-message", style={"marginBottom": "10px", "color": "#00ffcc"}),
    html.Div(id="kpi-content", className="kpi-container"),
    html.Div([
        html.Button("Add Current Chart", id="viz-save-chart", n_clicks=0),
        html.Button("Clear Added Charts", id="viz-clear-saved-charts", n_clicks=0, style={"marginLeft": "8px"}),
    ], style={"marginBottom": "10px"}),
    dcc.Graph(
        id="custom-visualization",
        config=INTERACTIVE_GRAPH_CONFIG,
    ),
    html.H4("Saved Custom Charts", style={"marginTop": "20px"}),
    html.Div(id="saved-visualization-content", className="chart-grid"),
    html.H4("All-Column Visualizations", style={"marginTop": "20px"}),
    html.Div(id="all-visualization-content", className="chart-grid")
])


def _coerce_numeric_like(df: pd.DataFrame, min_valid_ratio: float = 0.8) -> pd.DataFrame:
    df_copy = df.copy()
    for column in df_copy.select_dtypes(include="object").columns:
        converted = pd.to_numeric(df_copy[column], errors="coerce")
        if converted.notna().mean() >= min_valid_ratio:
            df_copy[column] = converted
    return df_copy


def _detect_datetime_columns(df: pd.DataFrame, min_valid_ratio: float = 0.7) -> list[str]:
    detected = []
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            detected.append(col)
            continue
        if df[col].dtype == "object":
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().mean() >= min_valid_ratio:
                detected.append(col)
    return detected


def _reduce_to_max_categories(
    df: pd.DataFrame,
    x_col: str | None,
    y_col: str | None,
    aggregation: str,
    max_bars: int,
    reduction_mode: str,
) -> tuple[pd.DataFrame, str | None, str | None]:
    if not x_col or x_col not in df.columns:
        return df, x_col, y_col

    unique_count = df[x_col].nunique(dropna=False)
    if unique_count <= max_bars:
        return df, x_col, y_col

    if reduction_mode == "bins" and y_col and y_col in df.columns and pd.api.types.is_numeric_dtype(df[y_col]):
        numeric_series = pd.to_numeric(df[y_col], errors="coerce")
        valid = numeric_series.dropna()
        if valid.nunique() >= 2:
            bins = min(max_bars, int(valid.nunique()))
            band_col = f"{y_col}_band"
            binned = pd.cut(numeric_series, bins=bins, include_lowest=True, duplicates="drop")
            working = df.assign(**{band_col: binned.astype(str)})

            if aggregation in {"sum", "mean", "min", "max"}:
                out_col = f"{aggregation}_{y_col}"
                grouped = working.groupby(band_col, dropna=False).agg(**{out_col: (y_col, aggregation)}).reset_index()
                return grouped, band_col, out_col

            grouped = working.groupby(band_col, dropna=False).size().reset_index(name="count")
            return grouped, band_col, "count"

    metric_col = None
    if y_col and y_col in df.columns and pd.api.types.is_numeric_dtype(df[y_col]):
        metric_col = y_col

    if metric_col:
        grouped = df.groupby(x_col, dropna=False)[metric_col].sum().reset_index(name=metric_col)
        target_y = metric_col
    else:
        grouped = df.groupby(x_col, dropna=False).size().reset_index(name="count")
        target_y = "count"

    grouped = grouped.sort_values(target_y, ascending=False)
    keep_count = max(max_bars - 1, 1)
    top = grouped.head(keep_count).copy()
    rest = grouped.iloc[keep_count:]
    if not rest.empty:
        other_value = rest[target_y].sum()
        top = pd.concat([top, pd.DataFrame([{x_col: "Other", target_y: other_value}])], ignore_index=True)
    return top, x_col, target_y


def _build_custom_figure(df: pd.DataFrame, chart_type: str, x_col: str | None, y_col: str | None,
                         color_col: str | None, size_col: str | None, aggregation: str,
                         normalize_percent: bool = False, max_bars: int = 6,
                         category_reduction: str = "bins", color_palette: str = "plotly"):
    working_df = df.copy()
    color_sequence = COLOR_PALETTES.get(color_palette, px.colors.qualitative.Plotly)

    if chart_type == "heatmap":
        numeric_df = working_df.select_dtypes(include="number")
        if numeric_df.shape[1] < 2:
            return px.scatter(title="Need at least two numeric columns for a correlation heatmap")
        return px.imshow(numeric_df.corr(numeric_only=True), text_auto=True, title="Numeric Correlation Heatmap")

    if not x_col and chart_type in {"bar", "line", "histogram", "box", "violin", "pie"}:
        x_col = working_df.columns[0]

    if chart_type in {"bar", "line", "pie", "pareto"} and x_col and aggregation != "none":
        if aggregation == "count":
            grouped = working_df.groupby(x_col, dropna=False).size().reset_index(name="count")
            y_col = "count"
        else:
            numeric_y = y_col if y_col and pd.api.types.is_numeric_dtype(working_df[y_col]) else None
            if not numeric_y:
                numeric_candidates = working_df.select_dtypes(include="number").columns.tolist()
                if not numeric_candidates:
                    grouped = working_df.groupby(x_col, dropna=False).size().reset_index(name="count")
                    y_col = "count"
                else:
                    numeric_y = numeric_candidates[0]
            if numeric_y:
                agg_output_col = f"{aggregation}_{numeric_y}"
                if agg_output_col == x_col:
                    agg_output_col = f"{agg_output_col}_value"
                grouped = (
                    working_df.groupby(x_col, dropna=False)
                    .agg(**{agg_output_col: (numeric_y, aggregation)})
                    .reset_index()
                )
                y_col = agg_output_col
        working_df = grouped

    if chart_type in {"bar", "line", "pie", "pareto"}:
        working_df, x_col, y_col = _reduce_to_max_categories(
            working_df,
            x_col=x_col,
            y_col=y_col,
            aggregation=aggregation,
            max_bars=max_bars,
            reduction_mode=category_reduction,
        )

    safe_color_col = color_col if color_col and color_col in working_df.columns else None

    if chart_type == "bar":
        if normalize_percent and y_col and y_col in working_df.columns and pd.api.types.is_numeric_dtype(working_df[y_col]):
            total = working_df[y_col].sum()
            if total:
                pct_col = f"{y_col}_pct"
                working_df[pct_col] = (working_df[y_col] / total) * 100
                y_col = pct_col
        return px.bar(
            working_df,
            x=x_col,
            y=y_col,
            color=safe_color_col,
            title=f"Bar: {y_col or 'count'} by {x_col}",
            color_discrete_sequence=color_sequence,
        )
    if chart_type == "line":
        if normalize_percent and y_col and y_col in working_df.columns and pd.api.types.is_numeric_dtype(working_df[y_col]):
            total = working_df[y_col].sum()
            if total:
                pct_col = f"{y_col}_pct"
                working_df[pct_col] = (working_df[y_col] / total) * 100
                y_col = pct_col
        return px.line(
            working_df,
            x=x_col,
            y=y_col,
            color=safe_color_col,
            title=f"Line: {y_col or 'count'} by {x_col}",
            color_discrete_sequence=color_sequence,
            markers=True,
        )
    if chart_type == "scatter":
        safe_size_col = size_col if size_col and size_col in working_df.columns else None
        return px.scatter(
            working_df,
            x=x_col,
            y=y_col,
            color=safe_color_col,
            size=safe_size_col,
            title=f"Scatter: {y_col} vs {x_col}",
            color_discrete_sequence=color_sequence,
        )
    if chart_type == "histogram":
        return px.histogram(
            working_df,
            x=x_col,
            color=safe_color_col,
            title=f"Histogram: {x_col}",
            histnorm="percent" if normalize_percent else None,
            color_discrete_sequence=color_sequence,
        )
    if chart_type == "box":
        return px.box(
            working_df,
            x=x_col,
            y=y_col,
            color=safe_color_col,
            title=f"Box Plot: {y_col or x_col}",
            color_discrete_sequence=color_sequence,
        )
    if chart_type == "violin":
        return px.violin(
            working_df,
            x=x_col,
            y=y_col,
            color=safe_color_col,
            box=True,
            points="all",
            title=f"Violin Plot: {y_col or x_col}",
            color_discrete_sequence=color_sequence,
        )
    if chart_type == "pie":
        if not y_col or not pd.api.types.is_numeric_dtype(working_df[y_col]):
            pie_df = working_df.groupby(x_col, dropna=False).size().reset_index(name="count")
            return px.pie(
                pie_df,
                names=x_col,
                values="count",
                title=f"Pie: share by {x_col}",
                color_discrete_sequence=color_sequence,
            )
        return px.pie(
            working_df,
            names=x_col,
            values=y_col,
            title=f"Pie: {y_col} share by {x_col}",
            color_discrete_sequence=color_sequence,
        )
    if chart_type == "pareto":
        if not x_col or x_col not in working_df.columns:
            return px.scatter(title="Choose an X column for Pareto chart")

        if not y_col or y_col not in working_df.columns or not pd.api.types.is_numeric_dtype(working_df[y_col]):
            pareto_df = working_df.groupby(x_col, dropna=False).size().reset_index(name="value")
            y_col = "value"
        else:
            pareto_df = working_df.groupby(x_col, dropna=False)[y_col].sum().reset_index(name=y_col)

        pareto_df = pareto_df.sort_values(y_col, ascending=False)
        total = pareto_df[y_col].sum()
        pareto_df["cumulative_pct"] = (pareto_df[y_col].cumsum() / total * 100) if total else 0

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=pareto_df[x_col],
                y=pareto_df[y_col],
                name="Value",
                marker_color=color_sequence[0],
            )
        )
        fig.add_trace(
            go.Scatter(
                x=pareto_df[x_col],
                y=pareto_df["cumulative_pct"],
                name="Cumulative %",
                mode="lines+markers",
                marker=dict(color="#facc15"),
                yaxis="y2",
            )
        )
        fig.update_layout(
            title=f"Pareto: {y_col} by {x_col}",
            yaxis=dict(title=y_col),
            yaxis2=dict(title="Cumulative %", overlaying="y", side="right", range=[0, 100]),
        )
        return fig

    return px.scatter(title="Unsupported chart type")


def _format_value_for_label(value, value_format: str, currency: str) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "N/A"
    if value_format == "percent":
        return f"{numeric:.2f}%"
    return format_compact_number(float(numeric), number_format=value_format, currency=currency)


def _style_figure(
    figure: go.Figure,
    chart_type: str,
    title: str | None,
    x_label: str | None,
    y_label: str | None,
    theme: str,
    palette: str,
    show_data_labels: bool,
    show_legend: bool,
    value_format: str,
    currency: str,
):
    figure.update_layout(
        template=theme or "plotly_white",
        title=title or figure.layout.title.text,
        legend_title_text="",
        hovermode="closest",
        margin=dict(l=40, r=20, t=60, b=40),
        showlegend=show_legend,
        colorway=COLOR_PALETTES.get(palette, px.colors.qualitative.Plotly),
    )

    if x_label:
        figure.update_xaxes(title_text=x_label)
    if y_label:
        figure.update_yaxes(title_text=y_label)

    if value_format in {"k", "m", "b"}:
        figure.update_yaxes(tickformat=".2s")
    elif value_format == "percent":
        figure.update_yaxes(ticksuffix="%")

    if chart_type == "pie":
        if show_data_labels:
            figure.update_traces(textinfo="label+percent", textposition="outside")
        else:
            figure.update_traces(textinfo="none")
        return figure

    if chart_type == "heatmap":
        if show_data_labels:
            figure.update_traces(texttemplate="%{z}")
        else:
            figure.update_traces(texttemplate=None)
        return figure

    if not show_data_labels:
        figure.update_traces(text=None)
        return figure

    for trace in figure.data:
        values = getattr(trace, "y", None)
        if values is None:
            continue
        formatted_labels = [_format_value_for_label(v, value_format, currency) for v in values]
        trace.text = formatted_labels
        if "textposition" in getattr(trace, "_valid_props", {}):
            if chart_type == "line":
                trace.textposition = "top center"
            elif chart_type == "scatter":
                trace.textposition = "top center"
            else:
                trace.textposition = "outside"

    return figure


def _apply_slicers(df: pd.DataFrame, slicer1_col: str | None, slicer1_values: list | None,
                   slicer2_col: str | None, slicer2_values: list | None) -> pd.DataFrame:
    filtered = df.copy()
    if slicer1_col and slicer1_col in filtered.columns and slicer1_values:
        filtered = filtered[filtered[slicer1_col].astype(str).isin([str(v) for v in slicer1_values])]
    if slicer2_col and slicer2_col in filtered.columns and slicer2_values:
        filtered = filtered[filtered[slicer2_col].astype(str).isin([str(v) for v in slicer2_values])]
    return filtered


def _compute_kpi_value(series: pd.Series, operation: str, top_n: int) -> float:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if operation == "sum":
        return numeric.sum()
    if operation == "mean":
        return numeric.mean()
    if operation == "min":
        return numeric.min()
    if operation == "max":
        return numeric.max()
    if operation == "range":
        return numeric.max() - numeric.min() if not numeric.empty else float("nan")
    if operation == "count":
        return numeric.count()
    if operation == "top":
        return numeric.nlargest(top_n).sum()
    if operation == "bottom":
        return numeric.nsmallest(top_n).sum()
    return numeric.sum()


def _build_all_column_visuals(df: pd.DataFrame):
    visuals = []
    datetime_cols = _detect_datetime_columns(df)

    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            visuals.append(
                dcc.Graph(
                    figure=px.histogram(df, x=col, title=f"Distribution: {col}"),
                    config=INTERACTIVE_GRAPH_CONFIG,
                )
            )
        elif col in datetime_cols:
            parsed = pd.to_datetime(df[col], errors="coerce")
            counts = parsed.dropna().dt.to_period("M").astype(str).value_counts().sort_index().reset_index()
            counts.columns = ["period", "count"]
            visuals.append(
                dcc.Graph(
                    figure=px.line(counts, x="period", y="count", title=f"Records over time: {col}"),
                    config=INTERACTIVE_GRAPH_CONFIG,
                )
            )
        else:
            counts = df[col].astype(str).fillna("N/A").value_counts().head(20).reset_index()
            counts.columns = [col, "count"]
            visuals.append(
                dcc.Graph(
                    figure=px.bar(counts, x=col, y="count", title=f"Top values: {col}"),
                    config=INTERACTIVE_GRAPH_CONFIG,
                )
            )

    return visuals


@dash.callback(
    Output("viz-x", "options"),
    Output("viz-y", "options"),
    Output("viz-color", "options"),
    Output("viz-size", "options"),
    Output("viz-kpi-column", "options"),
    Output("viz-slicer1-column", "options"),
    Output("viz-slicer2-column", "options"),
    Output("viz-x", "value"),
    Output("viz-y", "value"),
    Output("viz-chart-type", "value"),
    Output("viz-aggregation", "value"),
    Input("shared-dataset", "data"),
    Input("shared-visual-config", "data")
)
def update_viz_options(shared_dataset, shared_visual_config):
    if not shared_dataset or not shared_dataset.get("records"):
        return [], [], [], [], [], [], [], None, None, "bar", "none"

    df = _coerce_numeric_like(pd.DataFrame(shared_dataset["records"]))
    all_options = [{"label": col, "value": col} for col in df.columns]
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    numeric_options = [{"label": col, "value": col} for col in numeric_cols]

    chart_default = "bar"
    aggregation_default = "none"
    x_default = df.columns[0] if len(df.columns) else None
    y_default = numeric_cols[0] if numeric_cols else None

    if shared_visual_config:
        chart_default = shared_visual_config.get("chart_type", chart_default)
        aggregation_default = shared_visual_config.get("aggregation", aggregation_default) or aggregation_default
        x_default = shared_visual_config.get("x", x_default)
        y_default = shared_visual_config.get("y", y_default)

    return (
        all_options,
        all_options,
        ([{"label": "None", "value": ""}] + all_options),
        ([{"label": "None", "value": ""}] + numeric_options),
        numeric_options,
        all_options,
        all_options,
        x_default,
        y_default,
        chart_default,
        aggregation_default,
    )


@dash.callback(
    Output("viz-slicer1-values", "options"),
    Output("viz-slicer2-values", "options"),
    Input("shared-dataset", "data"),
    Input("viz-slicer1-column", "value"),
    Input("viz-slicer2-column", "value")
)
def update_slicer_value_options(shared_dataset, slicer1_col, slicer2_col):
    if not shared_dataset or not shared_dataset.get("records"):
        return [], []

    df = pd.DataFrame(shared_dataset["records"])

    def options_for(column):
        if not column or column not in df.columns:
            return []
        values = sorted(df[column].dropna().astype(str).unique().tolist())[:500]
        return [{"label": v, "value": v} for v in values]

    return options_for(slicer1_col), options_for(slicer2_col)


@dash.callback(
    Output("viz-kpi-definitions", "data"),
    Input("viz-add-kpi", "n_clicks"),
    Input("viz-clear-kpi", "n_clicks"),
    State("viz-kpi-definitions", "data"),
    State("viz-kpi-column", "value"),
    State("viz-kpi-operation", "value"),
    State("viz-kpi-n", "value"),
    State("viz-kpi-format", "value"),
    State("viz-kpi-currency", "value"),
    prevent_initial_call=True
)
def update_kpi_definitions(add_clicks, clear_clicks, definitions, column, operation, n_value, number_format, currency):
    triggered = ctx.triggered_id
    definitions = definitions or []

    if triggered == "viz-clear-kpi":
        return []

    if triggered == "viz-add-kpi" and column:
        definitions.append(
            {
                "column": column,
                "operation": operation,
                "n": n_value,
                "format": number_format,
                "currency": currency,
            }
        )
    return definitions


@dash.callback(
    Output("viz-user-charts", "data"),
    Input("viz-save-chart", "n_clicks"),
    Input("viz-clear-saved-charts", "n_clicks"),
    State("viz-user-charts", "data"),
    State("custom-visualization", "figure"),
    State("viz-title", "value"),
    prevent_initial_call=True,
)
def manage_saved_charts(save_clicks, clear_clicks, saved_charts, current_figure, chart_title):
    action = ctx.triggered_id
    saved_charts = saved_charts or []

    if action == "viz-clear-saved-charts":
        return []

    if action == "viz-save-chart" and current_figure:
        title = chart_title.strip() if chart_title and chart_title.strip() else current_figure.get("layout", {}).get("title", {}).get("text", "Custom Chart")
        saved_charts.append({"title": title, "figure": current_figure})
    return saved_charts


@dash.callback(
    Output("saved-visualization-content", "children"),
    Input("viz-user-charts", "data"),
)
def render_saved_charts(saved_charts):
    if not saved_charts:
        return [html.Div([html.P("No saved charts yet. Build a chart and click 'Add Current Chart'.")], className="kpi-card")]

    cards = []
    for index, item in enumerate(saved_charts, start=1):
        fig_dict = item.get("figure") if isinstance(item, dict) else None
        if not fig_dict:
            continue
        title = item.get("title", f"Custom Chart {index}")
        cards.append(
            html.Div([
                html.H5(title, style={"marginBottom": "8px"}),
                dcc.Graph(figure=go.Figure(fig_dict), config=INTERACTIVE_GRAPH_CONFIG),
            ], className="kpi-card", style={"padding": "14px"})
        )
    return cards

@dash.callback(
    Output("visualization-message", "children"),
    Output("kpi-content", "children"),
    Output("custom-visualization", "figure"),
    Output("all-visualization-content", "children"),
    Output("viz-figure-store", "data"),
    Input("shared-dataset", "data"),
    Input("viz-chart-type", "value"),
    Input("viz-x", "value"),
    Input("viz-y", "value"),
    Input("viz-color", "value"),
    Input("viz-size", "value"),
    Input("viz-aggregation", "value"),
    Input("viz-title", "value"),
    Input("viz-x-label", "value"),
    Input("viz-y-label", "value"),
    Input("viz-theme", "value"),
    Input("viz-palette", "value"),
    Input("viz-value-format", "value"),
    Input("viz-value-currency", "value"),
    Input("viz-style-options", "value"),
    Input("viz-max-bars", "value"),
    Input("viz-category-reduction", "value"),
    Input("viz-auto-toggle", "value"),
    Input("viz-user-charts", "data"),
    Input("viz-slicer1-column", "value"),
    Input("viz-slicer1-values", "value"),
    Input("viz-slicer2-column", "value"),
    Input("viz-slicer2-values", "value"),
    Input("viz-kpi-definitions", "data")
)
def render_visualizations(shared_dataset, chart_type, x_col, y_col, color_col, size_col, aggregation,
                          chart_title, x_label, y_label, theme, palette, value_format, value_currency, style_options,
                          max_bars, category_reduction, auto_toggle, saved_user_charts,
                          slicer1_col, slicer1_values, slicer2_col, slicer2_values, kpi_definitions):
    if not shared_dataset or not shared_dataset.get("records"):
        empty_fig = px.scatter(title="Upload data to start visualizing")
        return "No uploaded data found. Upload a dataset on the Ingestion page first.", [], empty_fig, [], []

    df = _coerce_numeric_like(pd.DataFrame(shared_dataset["records"]))
    df = _apply_slicers(df, slicer1_col, slicer1_values, slicer2_col, slicer2_values)
    if df.empty:
        empty_fig = px.scatter(title="Dataset is empty after slicers")
        return "Dataset is empty after slicers.", [], empty_fig, [], []

    kpi_cards = []
    for definition in (kpi_definitions or []):
        column = definition.get("column")
        if not column or column not in df.columns:
            continue
        operation = definition.get("operation", "sum")
        n_value = int(definition.get("n", 5))
        number_format = definition.get("format", "plain")
        currency = definition.get("currency", "USD")

        value = _compute_kpi_value(df[column], operation, n_value)
        display_value = format_compact_number(value, number_format=number_format, currency=currency)
        label_suffix = f" (N={n_value})" if operation in {"top", "bottom"} else ""
        kpi_cards.append(
            html.Div([
                html.H3(f"{operation.upper()} {column}{label_suffix}"),
                html.P(display_value, className="kpi-value"),
            ], className="kpi-card")
        )

    if not kpi_cards:
        kpi_cards = [html.Div([html.P("Add KPI definitions above to create custom KPI cards.")], className="kpi-card")]

    try:
        style_options = style_options or []
        show_data_labels = "labels" in style_options
        normalize_percent = "percent" in style_options
        show_legend = "legend" in style_options

        custom_figure = _build_custom_figure(
            df=df,
            chart_type=chart_type,
            x_col=x_col,
            y_col=y_col,
            color_col=(color_col or None),
            size_col=(size_col or None),
            aggregation=aggregation,
            normalize_percent=normalize_percent,
            max_bars=int(max_bars or 6),
            category_reduction=category_reduction or "bins",
            color_palette=palette or "plotly",
        )
        custom_figure = _style_figure(
            figure=custom_figure,
            chart_type=chart_type,
            title=chart_title,
            x_label=x_label,
            y_label=y_label,
            theme=theme,
            palette=palette or "plotly",
            show_data_labels=show_data_labels,
            show_legend=show_legend,
            value_format=value_format or "plain",
            currency=value_currency or "USD",
        )
    except Exception as exc:
        custom_figure = px.scatter(title=f"Visualization error: {exc}")

    all_visuals = _build_all_column_visuals(df) if auto_toggle and "auto" in auto_toggle else []
    all_figures = [custom_figure]
    for graph_component in all_visuals:
        all_figures.append(go.Figure(graph_component.figure))
    for saved in (saved_user_charts or []):
        fig_dict = saved.get("figure") if isinstance(saved, dict) else None
        if fig_dict:
            all_figures.append(go.Figure(fig_dict))
    message = f"Loaded {len(df):,} rows and {len(df.columns)} columns after slicers. Visuals are fully dynamic."

    return message, kpi_cards, custom_figure, all_visuals, [fig.to_dict() for fig in all_figures]


def _deserialize_figures(serialized_figures: list | None) -> list[go.Figure]:
    if not serialized_figures:
        return []
    return [go.Figure(fig_dict) for fig_dict in serialized_figures]


@dash.callback(
    Output("visuals-html-download", "data"),
    Input("export-visuals-html", "n_clicks"),
    State("viz-figure-store", "data"),
    prevent_initial_call=True
)
def export_visuals_html(n_clicks, stored_figures):
    figures = _deserialize_figures(stored_figures)
    if not figures:
        return None
    html_content = visuals_to_html(figures, title="Dynamic Visualizations")
    return dict(content=html_content, filename="visualizations.html", type="text/html")


@dash.callback(
    Output("visuals-pdf-download", "data"),
    Input("export-visuals-pdf", "n_clicks"),
    State("viz-figure-store", "data"),
    prevent_initial_call=True
)
def export_visuals_pdf(n_clicks, stored_figures):
    figures = _deserialize_figures(stored_figures)
    if not figures:
        return None
    pdf_bytes = visuals_to_pdf_bytes(figures, title="Dynamic Visualizations")
    return dcc.send_bytes(lambda stream: stream.write(pdf_bytes), "visualizations.pdf")


@dash.callback(
    Output("visuals-zip-download", "data"),
    Input("export-visuals-zip", "n_clicks"),
    State("viz-figure-store", "data"),
    prevent_initial_call=True
)
def export_visuals_zip(n_clicks, stored_figures):
    figures = _deserialize_figures(stored_figures)
    if not figures:
        return None
    zip_bytes = figures_to_zip_bytes(figures)
    return dcc.send_bytes(lambda stream: stream.write(zip_bytes), "visualizations_bundle.zip")
