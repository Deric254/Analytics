import dash
from dash import html, dcc, dash_table, Input, Output, State, no_update, ctx
import pandas as pd
from services.export_utils import dataframe_to_excel_bytes

dash.register_page(__name__, path="/cleaning", name="Data Cleaning")

layout = html.Div([
    html.H2("DericBI Analytics Engine - Data Cleaning", className="page-title"),
    dcc.Store(id="cleaning-raw-dataset", storage_type="session"),

    # Cleaning Options
    html.Div([
        html.Label("Handle Missing Values"),
        dcc.Dropdown(
            id="missing-values",
            options=[
                {"label": "No action", "value": "none"},
                {"label": "Drop rows", "value": "drop"},
                {"label": "Fill with mean", "value": "mean"},
                {"label": "Fill with median", "value": "median"},
                {"label": "Fill with mode", "value": "mode"},
                {"label": "Forward fill", "value": "ffill"},
                {"label": "Backward fill", "value": "bfill"}
            ],
            value="none",
            placeholder="Choose missing-value handling strategy"
        ),
        html.Label("Columns for missing-value action"),
        dcc.Dropdown(id="missing-columns", multi=True, placeholder="Default: all columns"),

        dcc.RadioItems(
            id="duplicate-scope",
            options=[
                {"label": "No action", "value": "none"},
                {"label": "Remove exact duplicate rows", "value": "all"},
                {"label": "Remove duplicates using selected columns", "value": "subset"}
            ],
            value="none"
        ),
        dcc.Dropdown(id="duplicate-subset-columns", multi=True, placeholder="Subset columns for duplicate removal"),

        html.Label("Type conversion"),
        dcc.Dropdown(id="type-convert-columns", multi=True, placeholder="Select columns to convert"),
        dcc.Dropdown(
            id="type-convert-target",
            options=[
                {"label": "To numeric", "value": "numeric"},
                {"label": "To text", "value": "text"},
                {"label": "To datetime", "value": "datetime"},
                {"label": "To category", "value": "category"}
            ],
            value="numeric",
            placeholder="Select target type"
        ),

        html.Label("Drop columns"),
        dcc.Dropdown(id="drop-columns", multi=True, placeholder="Optional columns to drop"),

        html.Label("Outlier treatment"),
        dcc.RadioItems(
            id="outlier-mode",
            options=[
                {"label": "No action", "value": "none"},
                {"label": "Remove outlier rows (Z-score)", "value": "remove"},
                {"label": "Cap outlier values (winsorize)", "value": "cap"}
            ],
            value="none"
        ),
        dcc.Dropdown(id="outlier-columns", multi=True, placeholder="Columns for outlier processing"),
        html.Label("Outlier Detection Threshold (Z-score)"),
        dcc.Slider(id="outlier-threshold", min=1, max=5, step=0.5, value=3),

        html.Label("Row filter (pandas query, optional)"),
        dcc.Input(id="row-filter-query", type="text", placeholder="e.g. Revenue > 1000 and Region == 'West'"),

        html.Button("Apply Cleaning", id="apply-cleaning", n_clicks=0, style={"marginTop": "10px"}),
    ], style={"marginTop": "20px"}),

    # Preview Table
    html.Div(id="cleaned-table", style={"marginTop": "20px"}),

    # Rollback Button
    html.Button("Rollback to Raw Data", id="rollback", n_clicks=0, style={"marginTop": "20px"}),
    html.Button("Export Cleaned CSV", id="export-cleaned-csv", n_clicks=0, style={"marginTop": "20px", "marginLeft": "8px"}),
    html.Button("Export Cleaned Excel", id="export-cleaned-xlsx", n_clicks=0, style={"marginTop": "20px", "marginLeft": "8px"}),
    dcc.Download(id="cleaned-csv-download"),
    dcc.Download(id="cleaned-xlsx-download"),

    # System Guidance
    html.Div(id="cleaning-message", style={"marginTop": "10px", "color": "green"})
])


def _serialize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    output = df.copy()
    for col in output.columns:
        if pd.api.types.is_datetime64_any_dtype(output[col]):
            output[col] = output[col].dt.strftime("%Y-%m-%d %H:%M:%S")
        elif str(output[col].dtype) == "category":
            output[col] = output[col].astype("string")
    return output


@dash.callback(
    Output("cleaning-raw-dataset", "data"),
    Input("shared-dataset", "data"),
    State("cleaning-raw-dataset", "data")
)
def cache_raw_dataset(shared_dataset, existing_raw):
    if not shared_dataset or not shared_dataset.get("records"):
        return no_update

    if shared_dataset.get("cleaning_applied"):
        return existing_raw if existing_raw else {
            "filename": shared_dataset.get("filename", "dataset"),
            "records": shared_dataset.get("records", [])
        }

    return {
        "filename": shared_dataset.get("filename", "dataset"),
        "records": shared_dataset.get("records", [])
    }


@dash.callback(
    Output("missing-columns", "options"),
    Output("duplicate-subset-columns", "options"),
    Output("type-convert-columns", "options"),
    Output("drop-columns", "options"),
    Output("outlier-columns", "options"),
    Input("shared-dataset", "data")
)
def update_cleaning_column_options(shared_dataset):
    if not shared_dataset or not shared_dataset.get("records"):
        return [], [], [], [], []

    df = pd.DataFrame(shared_dataset["records"])
    options = [{"label": col, "value": col} for col in df.columns]
    return options, options, options, options, options

@dash.callback(
    Output("cleaned-table", "children"),
    Output("cleaning-message", "children"),
    Output("shared-dataset", "data", allow_duplicate=True),
    Input("apply-cleaning", "n_clicks"),
    Input("rollback", "n_clicks"),
    Input("missing-values", "value"),
    Input("missing-columns", "value"),
    Input("duplicate-scope", "value"),
    Input("duplicate-subset-columns", "value"),
    Input("type-convert-columns", "value"),
    Input("type-convert-target", "value"),
    Input("drop-columns", "value"),
    Input("outlier-mode", "value"),
    Input("outlier-columns", "value"),
    Input("outlier-threshold", "value"),
    Input("row-filter-query", "value"),
    State("shared-dataset", "data"),
    State("cleaning-raw-dataset", "data"),
    prevent_initial_call=True,
)
def clean_data(
    apply_clicks,
    rollback_clicks,
    missing_strategy,
    missing_columns,
    duplicate_scope,
    duplicate_subset_columns,
    type_convert_columns,
    type_convert_target,
    drop_columns,
    outlier_mode,
    outlier_columns,
    threshold,
    row_filter_query,
    shared_dataset,
    raw_dataset,
):
    active_dataset = shared_dataset if shared_dataset and shared_dataset.get("records") else raw_dataset
    if not active_dataset or not active_dataset.get("records"):
        return html.Div("No uploaded data found. Upload a dataset on the Ingestion page first."), "Waiting for uploaded dataset.", no_update

    triggered_id = ctx.triggered_id

    if triggered_id == "rollback":
        if not raw_dataset or not raw_dataset.get("records"):
            return html.Div("No raw dataset snapshot available yet."), "Nothing to roll back.", no_update

        restored_df = pd.DataFrame(raw_dataset["records"])
        return dash_table.DataTable(
            data=restored_df.head(50).to_dict("records"),
            columns=[{"name": i, "id": i} for i in restored_df.columns],
            page_size=10,
            style_table={"overflowX": "auto"}
        ), "Rolled back to raw dataset.", raw_dataset

    if triggered_id != "apply-cleaning" and apply_clicks == 0:
        preview_df = pd.DataFrame(active_dataset["records"])
        return dash_table.DataTable(
            data=preview_df.head(50).to_dict("records"),
            columns=[{"name": i, "id": i} for i in preview_df.columns],
            page_size=10,
            style_table={"overflowX": "auto"}
        ), "Choose cleaning options and click Apply Cleaning.", no_update

    df_copy = pd.DataFrame(active_dataset["records"]).copy()
    before_rows = len(df_copy)
    messages = []

    if type_convert_columns:
        for column in type_convert_columns:
            if column not in df_copy.columns:
                continue
            if type_convert_target == "numeric":
                df_copy[column] = pd.to_numeric(df_copy[column], errors="coerce")
            elif type_convert_target == "datetime":
                df_copy[column] = pd.to_datetime(df_copy[column], errors="coerce")
            elif type_convert_target == "text":
                mask = df_copy[column].notna()
                df_copy.loc[mask, column] = df_copy.loc[mask, column].astype(str)
            elif type_convert_target == "category":
                df_copy[column] = df_copy[column].astype("category")
        messages.append(f"Converted {len(type_convert_columns)} column(s) to {type_convert_target}.")

    missing_targets = [col for col in (missing_columns or df_copy.columns.tolist()) if col in df_copy.columns]
    if missing_strategy == "drop":
        df_copy = df_copy.dropna(subset=missing_targets)
        messages.append("Dropped rows with missing values.")
    elif missing_strategy == "mean":
        numeric_targets = [col for col in missing_targets if pd.api.types.is_numeric_dtype(df_copy[col])]
        for col in numeric_targets:
            df_copy[col] = df_copy[col].fillna(df_copy[col].mean())
        messages.append("Filled missing numeric values with mean.")
    elif missing_strategy == "median":
        numeric_targets = [col for col in missing_targets if pd.api.types.is_numeric_dtype(df_copy[col])]
        for col in numeric_targets:
            df_copy[col] = df_copy[col].fillna(df_copy[col].median())
        messages.append("Filled missing numeric values with median.")
    elif missing_strategy == "mode":
        for col in missing_targets:
            mode_series = df_copy[col].mode(dropna=True)
            if not mode_series.empty:
                df_copy[col] = df_copy[col].fillna(mode_series.iloc[0])
        messages.append("Filled missing values with mode.")
    elif missing_strategy == "ffill":
        df_copy[missing_targets] = df_copy[missing_targets].ffill()
        messages.append("Applied forward fill.")
    elif missing_strategy == "bfill":
        df_copy[missing_targets] = df_copy[missing_targets].bfill()
        messages.append("Applied backward fill.")

    if duplicate_scope == "all":
        df_copy = df_copy.drop_duplicates()
        messages.append("Removed exact duplicate rows.")
    elif duplicate_scope == "subset" and duplicate_subset_columns:
        subset = [col for col in duplicate_subset_columns if col in df_copy.columns]
        if subset:
            df_copy = df_copy.drop_duplicates(subset=subset)
            messages.append(f"Removed duplicates using {len(subset)} selected columns.")

    if drop_columns:
        removable = [col for col in drop_columns if col in df_copy.columns]
        if removable:
            df_copy = df_copy.drop(columns=removable)
            messages.append(f"Dropped {len(removable)} column(s).")

    if row_filter_query:
        try:
            df_copy = df_copy.query(row_filter_query)
            messages.append("Applied row filter query.")
        except Exception as exc:
            return dash_table.DataTable(
                data=df_copy.head(50).to_dict("records"),
                columns=[{"name": i, "id": i} for i in df_copy.columns],
                page_size=10,
                style_table={"overflowX": "auto"}
            ), f"Filter query failed: {exc}", no_update

    numeric_cols = df_copy.select_dtypes(include="number").columns.tolist()
    outlier_targets = [col for col in (outlier_columns or numeric_cols) if col in numeric_cols]
    if outlier_mode in {"remove", "cap"} and outlier_targets:
        if outlier_mode == "remove":
            keep_mask = pd.Series([True] * len(df_copy), index=df_copy.index)
            for col in outlier_targets:
                std_dev = df_copy[col].std()
                if pd.isna(std_dev) or std_dev == 0:
                    continue
                z_scores = (df_copy[col] - df_copy[col].mean()) / std_dev
                keep_mask = keep_mask & (z_scores.abs() <= threshold)
            df_copy = df_copy[keep_mask]
            messages.append("Removed outlier rows using Z-score threshold.")
        else:
            for col in outlier_targets:
                std_dev = df_copy[col].std()
                if pd.isna(std_dev) or std_dev == 0:
                    continue
                mean = df_copy[col].mean()
                lower = mean - threshold * std_dev
                upper = mean + threshold * std_dev
                df_copy[col] = df_copy[col].clip(lower=lower, upper=upper)
            messages.append("Capped outlier values using Z-score bounds.")

    df_copy = df_copy.reset_index(drop=True)
    serialized_df = _serialize_dataframe(df_copy)
    updated_dataset = {
        "filename": active_dataset.get("filename", "dataset"),
        "records": serialized_df.to_dict("records"),
        "cleaning_applied": True,
    }

    after_rows = len(df_copy)
    info = f"Rows: {before_rows:,} → {after_rows:,}. "
    details = " ".join(messages) if messages else "No transformation selected."

    return dash_table.DataTable(
        data=serialized_df.head(50).to_dict("records"),
        columns=[{"name": i, "id": i} for i in serialized_df.columns],
        page_size=10,
        style_table={"overflowX": "auto"}
    ), f"{info}{details}", updated_dataset


@dash.callback(
    Output("cleaned-csv-download", "data"),
    Input("export-cleaned-csv", "n_clicks"),
    State("shared-dataset", "data"),
    prevent_initial_call=True
)
def export_cleaned_csv(n_clicks, shared_dataset):
    if not shared_dataset or not shared_dataset.get("records"):
        return None

    df = pd.DataFrame(shared_dataset["records"])
    return dcc.send_data_frame(df.to_csv, "cleaned_dataset.csv", index=False)


@dash.callback(
    Output("cleaned-xlsx-download", "data"),
    Input("export-cleaned-xlsx", "n_clicks"),
    State("shared-dataset", "data"),
    prevent_initial_call=True
)
def export_cleaned_excel(n_clicks, shared_dataset):
    if not shared_dataset or not shared_dataset.get("records"):
        return None

    df = pd.DataFrame(shared_dataset["records"])
    excel_bytes = dataframe_to_excel_bytes(df)
    return dcc.send_bytes(lambda stream: stream.write(excel_bytes), "cleaned_dataset.xlsx")
