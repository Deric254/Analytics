from dash import html
import pandas as pd
from dash import dash_table
from services.export_utils import build_exhaustive_report_data


def _format_value(value):
    if pd.isna(value):
        return "N/A"
    if isinstance(value, (int, float)):
        if abs(value) >= 1000:
            return f"{value:,.2f}"
        return f"{value:.4g}"
    return str(value)


def _coerce_numeric_like(df: pd.DataFrame, min_valid_ratio: float = 0.8) -> pd.DataFrame:
    df_copy = df.copy()
    for column in df_copy.select_dtypes(include="object").columns:
        converted = pd.to_numeric(df_copy[column], errors="coerce")
        valid_ratio = converted.notna().mean()
        if valid_ratio >= min_valid_ratio:
            df_copy[column] = converted
    return df_copy


def _detect_date_columns(df: pd.DataFrame, min_valid_ratio: float = 0.7) -> list[str]:
    detected = []
    for column in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            detected.append(column)
            continue

        if df[column].dtype == "object":
            parsed = pd.to_datetime(df[column], errors="coerce")
            if parsed.notna().mean() >= min_valid_ratio:
                detected.append(column)
    return detected


def build_report_component(report_data: dict, layout_choice: str = "system"):
    overview = report_data["overview"]
    numeric_summary = report_data["numeric_summary"]
    categorical_summary = report_data["categorical_summary"]
    sample_rows = report_data["sample_rows"]

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
            html.Li(f"Missing values: {overview['missing_values']:,} ({overview['missing_percent']:.2f}%)"),
        ]),
        html.H4("Numeric Summary"),
        dash_table.DataTable(
            data=numeric_summary.round(4).to_dict("records") if not numeric_summary.empty else [],
            columns=[{"name": c, "id": c} for c in numeric_summary.columns] if not numeric_summary.empty else [],
            page_size=10,
            style_table={"overflowX": "auto"}
        ) if not numeric_summary.empty else html.P("No numeric columns available."),
        html.H4("Categorical Summary"),
        dash_table.DataTable(
            data=categorical_summary.to_dict("records") if not categorical_summary.empty else [],
            columns=[{"name": c, "id": c} for c in categorical_summary.columns] if not categorical_summary.empty else [],
            page_size=10,
            style_table={"overflowX": "auto"}
        ) if not categorical_summary.empty else html.P("No categorical/text columns available."),
        html.H4("Sample Records"),
        dash_table.DataTable(
            data=sample_rows.to_dict("records") if not sample_rows.empty else [],
            columns=[{"name": c, "id": c} for c in sample_rows.columns] if not sample_rows.empty else [],
            page_size=10,
            style_table={"overflowX": "auto"}
        ) if not sample_rows.empty else html.P("No sample rows available."),
    ])


def generate_report(df: pd.DataFrame, layout_choice: str = "system", source_name: str = "dataset"):
    if df is None or df.empty:
        return html.Div("No dataset available to generate report."), None

    analyzed_df = _coerce_numeric_like(df)
    report_data = build_exhaustive_report_data(analyzed_df, source_name=source_name)
    component = build_report_component(report_data=report_data, layout_choice=layout_choice)
    return component, report_data
