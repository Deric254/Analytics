from dash import html, dash_table
import pandas as pd
from services.export_utils import build_exhaustive_report_data


def _coerce_numeric_like(df: pd.DataFrame, min_valid_ratio: float = 0.8) -> pd.DataFrame:
    df_copy = df.copy()
    for col in df_copy.select_dtypes(include="object").columns:
        converted = pd.to_numeric(df_copy[col], errors="coerce")
        if converted.notna().mean() >= min_valid_ratio:
            df_copy[col] = converted
    return df_copy


def build_report_component(report_data: dict, layout_choice: str = "system"):
    overview = report_data["overview"]
    numeric_summary = report_data["numeric_summary"]
    categorical_summary = report_data["categorical_summary"]
    sample_rows = report_data["sample_rows"]

    def make_table(frame):
        if frame.empty:
            return None
        return dash_table.DataTable(
            data=frame.round(4).to_dict("records")
            if frame.select_dtypes(include="number").shape[1] > 0
            else frame.to_dict("records"),
            columns=[{"name": c, "id": c} for c in frame.columns],
            page_size=10,
            style_table={"overflowX": "auto"},
        )

    return html.Div([
        html.H3("Dataset Report"),
        html.P(f"Layout: {layout_choice.title()}"),
        html.P(f"Source: {overview['source']}"),
        html.P(f"Generated: {overview['generated_at']}"),
        html.H4("Overview"),
        html.Ul([
            html.Li(f"Rows: {overview['rows']:,}"),
            html.Li(f"Columns: {overview['columns']}"),
            html.Li(f"Numeric columns: {overview['numeric_columns']}"),
            html.Li(f"Categorical/text columns: {overview['categorical_columns']}"),
            html.Li(
                f"Missing values: {overview['missing_values']:,} "
                f"({overview['missing_percent']:.2f}%)"
            ),
        ]),
        html.H4("Numeric Summary"),
        make_table(numeric_summary) or html.P("No numeric columns available."),
        html.H4("Categorical Summary"),
        make_table(categorical_summary) or html.P("No categorical columns available."),
        html.H4("Sample Records"),
        make_table(sample_rows) or html.P("No sample rows available."),
    ])


def generate_report(
    df: pd.DataFrame, layout_choice: str = "system", source_name: str = "dataset"
):
    if df is None or df.empty:
        return html.Div("No dataset available to generate report."), None
    analyzed_df = _coerce_numeric_like(df)
    report_data = build_exhaustive_report_data(analyzed_df, source_name=source_name)
    component = build_report_component(
        report_data=report_data, layout_choice=layout_choice
    )
    return component, report_data
