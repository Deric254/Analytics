"""
Cleaning page — only fires on explicit Apply click. Clean UI with results summary.
"""
import dash
from dash import html, dcc, dash_table, Input, Output, State, no_update, ctx, ALL
import pandas as pd
from services.export_utils import dataframe_to_excel_bytes

dash.register_page(__name__, path="/cleaning", name="Data Cleaning")

layout = html.Div([
    html.H2("Data Cleaning", style={"marginBottom": "4px", "color": "#1f2937"}),
    html.P("Configure cleaning options then click Apply. Use Rollback to undo.",
           style={"color": "#6b7280", "marginBottom": "20px", "fontSize": "13px"}),

    dcc.Store(id="cleaning-raw-dataset", storage_type="session"),

    html.Div([
        # Left panel: options
        html.Div([
            html.Div([
                html.H4("Missing Values", style={"fontSize": "13px", "fontWeight": "700", "color": "#374151", "marginBottom": "8px"}),
                dcc.Dropdown(id="missing-values", options=[
                    {"label": "No action",          "value": "none"},
                    {"label": "Drop rows",           "value": "drop"},
                    {"label": "Fill — mean",         "value": "mean"},
                    {"label": "Fill — median",       "value": "median"},
                    {"label": "Fill — mode",         "value": "mode"},
                    {"label": "Forward fill",        "value": "ffill"},
                    {"label": "Backward fill",       "value": "bfill"},
                ], value="none", clearable=False),
                html.Label("Columns (default: all)", style={"fontSize": "12px", "color": "#6b7280", "marginTop": "6px"}),
                dcc.Dropdown(id="missing-columns", multi=True, placeholder="All columns"),
            ], style={"marginBottom": "16px"}),

            html.Div([
                html.H4("Duplicates", style={"fontSize": "13px", "fontWeight": "700", "color": "#374151", "marginBottom": "8px"}),
                dcc.RadioItems(id="duplicate-scope", options=[
                    {"label": "No action",                             "value": "none"},
                    {"label": "Remove exact duplicates",               "value": "all"},
                    {"label": "Remove duplicates by selected columns", "value": "subset"},
                ], value="none", labelStyle={"display": "block", "marginBottom": "4px"}),
                dcc.Dropdown(id="duplicate-subset-columns", multi=True, placeholder="Subset columns"),
            ], style={"marginBottom": "16px"}),

            html.Div([
                html.H4("Type Conversion", style={"fontSize": "13px", "fontWeight": "700", "color": "#374151", "marginBottom": "8px"}),
                dcc.Dropdown(id="type-convert-columns", multi=True, placeholder="Select columns"),
                dcc.Dropdown(id="type-convert-target", options=[
                    {"label": "To numeric",  "value": "numeric"},
                    {"label": "To text",     "value": "text"},
                    {"label": "To datetime", "value": "datetime"},
                    {"label": "To category", "value": "category"},
                ], value="numeric", clearable=False, style={"marginTop": "6px"}),
            ], style={"marginBottom": "16px"}),

            html.Div([
                html.H4("Drop Columns", style={"fontSize": "13px", "fontWeight": "700", "color": "#374151", "marginBottom": "8px"}),
                dcc.Dropdown(id="drop-columns", multi=True, placeholder="Select columns to drop"),
            ], style={"marginBottom": "16px"}),

            html.Div([
                html.H4("Outlier Treatment", style={"fontSize": "13px", "fontWeight": "700", "color": "#374151", "marginBottom": "8px"}),
                dcc.RadioItems(id="outlier-mode", options=[
                    {"label": "No action",         "value": "none"},
                    {"label": "Remove rows",       "value": "remove"},
                    {"label": "Cap values",        "value": "cap"},
                ], value="none", labelStyle={"display": "block", "marginBottom": "4px"}),
                dcc.Dropdown(id="outlier-columns", multi=True, placeholder="Columns (default: all numeric)"),
                html.Label("Z-score threshold", style={"fontSize": "12px", "color": "#6b7280", "marginTop": "8px"}),
                dcc.Slider(id="outlier-threshold", min=1, max=5, step=0.5, value=3,
                           marks={1: "1", 2: "2", 3: "3", 4: "4", 5: "5"}),
            ], style={"marginBottom": "16px"}),

            html.Div([
                html.H4("Row Filter", style={"fontSize": "13px", "fontWeight": "700", "color": "#374151", "marginBottom": "8px"}),
                dcc.Input(id="row-filter-query", type="text",
                          placeholder="e.g.  Revenue > 1000 and Region == 'West'",
                          style={"width": "100%", "padding": "7px", "borderRadius": "6px", "border": "1px solid #d1d5db"}),
            ], style={"marginBottom": "20px"}),


            html.Div([
                html.H4("Rename Columns", style={"fontSize":"13px","fontWeight":"700","color":"#374151","marginBottom":"8px"}),
                html.Div(id="rename-pairs-container", children=[
                    html.Div([
                        dcc.Dropdown(id={"type":"rename-col","index":0}, placeholder="Column to rename",
                                     style={"flex":"1","marginRight":"6px"}),
                        dcc.Input(id={"type":"rename-new","index":0}, type="text", placeholder="New name",
                                  style={"flex":"1","padding":"6px 8px","borderRadius":"6px",
                                         "border":"1px solid #d1d5db","fontSize":"13px"}),
                    ], style={"display":"flex","marginBottom":"6px"}),
                ]),
                html.Div([
                    html.Button("+ Add pair", id="rename-add-btn", n_clicks=0,
                                style={"fontSize":"12px","color":"#3e8865","background":"none",
                                       "border":"none","cursor":"pointer","padding":"0","fontWeight":"600"}),
                ]),
                dcc.Store(id="rename-count", data=1),
            ], style={"marginBottom":"16px"}),

            html.Div([
                html.H4("Trim & Standardise Text", style={"fontSize":"13px","fontWeight":"700","color":"#374151","marginBottom":"8px"}),
                dcc.Dropdown(id="text-clean-columns", multi=True, placeholder="Columns (default: all text)"),
                dcc.Checklist(id="text-clean-ops", options=[
                    {"label":" Trim whitespace",       "value":"trim"},
                    {"label":" Uppercase",              "value":"upper"},
                    {"label":" Lowercase",              "value":"lower"},
                    {"label":" Title case",             "value":"title"},
                ], value=["trim"],
                labelStyle={"display":"block","fontSize":"13px","marginBottom":"3px"},
                style={"marginTop":"8px"}),
            ], style={"marginBottom":"16px"}),

            html.Div([
                html.H4("Replace Values", style={"fontSize":"13px","fontWeight":"700","color":"#374151","marginBottom":"8px"}),
                html.P("Comma-separated values to treat as missing (e.g. N/A, -, unknown, 0)",
                       style={"fontSize":"11px","color":"#6b7280","margin":"0 0 6px"}),
                dcc.Input(id="replace-find", type="text", placeholder="e.g.  N/A, -, unknown",
                          style={"width":"100%","padding":"7px","borderRadius":"6px",
                                 "border":"1px solid #d1d5db","marginBottom":"6px","fontSize":"13px"}),
                dcc.Input(id="replace-with", type="text", placeholder="Replace with (blank = NaN)",
                          style={"width":"100%","padding":"7px","borderRadius":"6px",
                                 "border":"1px solid #d1d5db","fontSize":"13px"}),
            ], style={"marginBottom":"20px"}),
            html.Div([
                html.Button("✅ Apply Cleaning", id="apply-cleaning", n_clicks=0, style={
                    "padding": "9px 20px", "borderRadius": "6px", "border": "none",
                    "background": "#3e8865", "color": "#fff", "fontWeight": "700", "cursor": "pointer", "marginRight": "8px",
                }),
                html.Button("↩ Rollback", id="rollback", n_clicks=0, style={
                    "padding": "9px 16px", "borderRadius": "6px", "border": "1px solid #d1d5db",
                    "background": "#fff", "fontWeight": "600", "cursor": "pointer",
                }),
            ]),
        ], style={
            "width": "280px", "flexShrink": "0",
            "background": "#fff", "borderRadius": "10px", "padding": "20px",
            "boxShadow": "0 1px 6px rgba(0,0,0,0.07)", "border": "1px solid #e5e7eb",
            "alignSelf": "flex-start",
        }),

        # Right panel: output
        html.Div([
            html.Div(id="cleaning-message", style={"marginBottom": "12px"}),
            html.Div(id="cleaned-table"),
            html.Div([
                html.Button("⬇ Export CSV", id="export-cleaned-csv", n_clicks=0, style={
                    "marginRight": "8px", "padding": "7px 14px", "borderRadius": "6px",
                    "border": "1px solid #3e8865", "background": "#fff", "color": "#3e8865", "cursor": "pointer",
                }),
                html.Button("⬇ Export Excel", id="export-cleaned-xlsx", n_clicks=0, style={
                    "padding": "7px 14px", "borderRadius": "6px",
                    "border": "1px solid #3e8865", "background": "#fff", "color": "#3e8865", "cursor": "pointer",
                }),
                dcc.Download(id="cleaned-csv-download"),
                dcc.Download(id="cleaned-xlsx-download"),
            ], style={"marginTop": "14px"}),
        ], style={"flex": "1", "minWidth": "0"}),
    ], style={"display": "flex", "gap": "16px", "alignItems": "flex-start"}),
])


def _serialize_df(df):
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%Y-%m-%d %H:%M:%S")
        elif str(out[col].dtype) == "category":
            out[col] = out[col].astype("string")
    return out


def _ok(text):
    return html.Div(text, style={"background": "rgba(34,197,94,0.1)", "color": "#15803d",
                                  "padding": "10px 14px", "borderRadius": "8px", "border": "1px solid rgba(34,197,94,0.3)", "fontSize": "13px"})

def _info(text):
    return html.Div(text, style={"background": "rgba(99,102,241,0.08)", "color": "#4338ca",
                                  "padding": "10px 14px", "borderRadius": "8px", "fontSize": "13px"})

def _err(text):
    return html.Div(text, style={"background": "rgba(239,68,68,0.08)", "color": "#dc2626",
                                  "padding": "10px 14px", "borderRadius": "8px", "fontSize": "13px"})


def _make_table(df):
    return dash_table.DataTable(
        data=df.head(50).to_dict("records"),
        columns=[{"name": c, "id": c} for c in df.columns],
        style_table={"overflowX": "auto"},
        style_header={"background": "#f3f4f6", "fontWeight": "700", "fontSize": "12px"},
        style_cell={"fontSize": "12px", "padding": "6px 10px"},
        style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#fafafa"}],
        page_size=10,
    )


@dash.callback(
    Output("cleaning-raw-dataset", "data"),
    Input("shared-dataset", "data"),
    State("cleaning-raw-dataset", "data"),
)
def cache_raw(shared_dataset, existing_raw):
    if not shared_dataset or not shared_dataset.get("records"):
        return no_update
    if shared_dataset.get("cleaning_applied"):
        return existing_raw or {"filename": shared_dataset.get("filename", "dataset"), "records": shared_dataset["records"]}
    return {"filename": shared_dataset.get("filename", "dataset"), "records": shared_dataset["records"]}



@dash.callback(
    Output("rename-pairs-container", "children"),
    Output("rename-count", "data"),
    Input("rename-add-btn", "n_clicks"),
    Input("shared-dataset", "data"),
    State("rename-count", "data"),
    prevent_initial_call=True,
)
def manage_rename_pairs(_, shared_dataset, count):
    triggered = ctx.triggered_id
    opts = []
    if shared_dataset and shared_dataset.get("records"):
        df_tmp = pd.DataFrame(shared_dataset["records"])
        opts = [{"label": c, "value": c} for c in df_tmp.columns]

    new_count = count + 1 if triggered == "rename-add-btn" else count

    def make_pair(i):
        return html.Div([
            dcc.Dropdown(id={"type":"rename-col","index":i}, options=opts,
                         placeholder="Column to rename",
                         style={"flex":"1","marginRight":"6px"}),
            dcc.Input(id={"type":"rename-new","index":i}, type="text",
                      placeholder="New name",
                      style={"flex":"1","padding":"6px 8px","borderRadius":"6px",
                             "border":"1px solid #d1d5db","fontSize":"13px"}),
        ], style={"display":"flex","marginBottom":"6px"})

    return [make_pair(i) for i in range(new_count)], new_count


@dash.callback(
    Output("missing-columns", "options"),
    Output("duplicate-subset-columns", "options"),
    Output("type-convert-columns", "options"),
    Output("drop-columns", "options"),
    Output("outlier-columns", "options"),
    Output("text-clean-columns", "options"),
    Input("shared-dataset", "data"),
)
def update_col_options(shared_dataset):
    if not shared_dataset or not shared_dataset.get("records"):
        return [], [], [], [], [], []
    df = pd.DataFrame(shared_dataset["records"])
    opts = [{"label": c, "value": c} for c in df.columns]
    text_opts = [{"label": c, "value": c} for c in df.select_dtypes(include="object").columns]
    return opts, opts, opts, opts, opts, text_opts


@dash.callback(
    Output("cleaned-table", "children"),
    Output("cleaning-message", "children"),
    Output("shared-dataset", "data", allow_duplicate=True),
    Input("apply-cleaning", "n_clicks"),
    Input("rollback", "n_clicks"),
    State("missing-values", "value"),
    State("missing-columns", "value"),
    State("duplicate-scope", "value"),
    State("duplicate-subset-columns", "value"),
    State("type-convert-columns", "value"),
    State("type-convert-target", "value"),
    State("drop-columns", "value"),
    State("outlier-mode", "value"),
    State("outlier-columns", "value"),
    State("outlier-threshold", "value"),
    State("row-filter-query", "value"),
    State({"type":"rename-col","index":ALL}, "value"),
    State({"type":"rename-new","index":ALL}, "value"),
    State("text-clean-columns", "value"),
    State("text-clean-ops", "value"),
    State("replace-find", "value"),
    State("replace-with", "value"),
    State("shared-dataset", "data"),
    State("cleaning-raw-dataset", "data"),
    prevent_initial_call=True,
)
def clean_data(apply_clicks, rollback_clicks,
               missing_strategy, missing_columns, duplicate_scope, duplicate_subset_columns,
               type_convert_columns, type_convert_target, drop_columns,
               outlier_mode, outlier_columns, threshold, row_filter_query,
               rename_cols, rename_news, text_clean_cols, text_clean_ops,
               replace_find, replace_with,
               shared_dataset, raw_dataset):

    active = shared_dataset if shared_dataset and shared_dataset.get("records") else raw_dataset
    if not active or not active.get("records"):
        return html.Div(), _err("No data loaded. Go to Ingestion first."), no_update

    triggered = ctx.triggered_id

    if triggered == "rollback":
        if not raw_dataset or not raw_dataset.get("records"):
            return html.Div(), _info("No raw snapshot available."), no_update
        df = pd.DataFrame(raw_dataset["records"])
        return _make_table(df), _ok(f"↩ Rolled back to raw data — {len(df):,} rows"), raw_dataset

    if triggered != "apply-cleaning":
        return no_update, no_update, no_update

    df = pd.DataFrame(active["records"]).copy()
    before = len(df)
    msgs = []

    # Rename columns
    if rename_cols and rename_news:
        rename_map = {o: n.strip() for o, n in zip(rename_cols, rename_news)
                      if o and n and n.strip() and o in df.columns and n.strip() != o}
        if rename_map:
            df = df.rename(columns=rename_map)
            msgs.append(f"Renamed {len(rename_map)} column(s): " +
                        ", ".join(f"{o}→{n}" for o, n in rename_map.items()))

    # Trim & standardise text
    if text_clean_ops:
        text_targets = [c for c in (text_clean_cols or [])
                        if c in df.columns and df[c].dtype == object]
        if not text_clean_cols:
            text_targets = df.select_dtypes(include="object").columns.tolist()
        for col in text_targets:
            if "trim"  in text_clean_ops: df[col] = df[col].astype(str).str.strip().where(df[col].notna())
            if "upper" in text_clean_ops: df[col] = df[col].astype(str).str.upper().where(df[col].notna())
            if "lower" in text_clean_ops: df[col] = df[col].astype(str).str.lower().where(df[col].notna())
            if "title" in text_clean_ops: df[col] = df[col].astype(str).str.title().where(df[col].notna())
        if text_targets:
            ops_done = ", ".join(text_clean_ops or [])
            msgs.append(f"Text cleaned ({ops_done}) on {len(text_targets)} column(s)")

    # Replace values
    if replace_find:
        find_vals = [v.strip() for v in replace_find.split(",") if v.strip()]
        with_val  = replace_with.strip() if replace_with and replace_with.strip() else None
        if find_vals:
            replaced = 0
            for col in df.columns:
                mask = df[col].astype(str).isin(find_vals)
                if mask.any():
                    df.loc[mask, col] = with_val
                    replaced += int(mask.sum())
            if replaced:
                msgs.append(f"Replaced {replaced:,} value(s): {', '.join(find_vals)} → "
                            f"{'NaN' if with_val is None else repr(with_val)}")


    # Type conversion first (affects what follows)
    if type_convert_columns:
        for col in type_convert_columns:
            if col not in df.columns: continue
            if type_convert_target == "numeric":
                df[col] = pd.to_numeric(df[col], errors="coerce")
            elif type_convert_target == "datetime":
                df[col] = pd.to_datetime(df[col], errors="coerce")
            elif type_convert_target == "text":
                df.loc[df[col].notna(), col] = df.loc[df[col].notna(), col].astype(str)
            elif type_convert_target == "category":
                df[col] = df[col].astype("category")
        msgs.append(f"Converted {len(type_convert_columns)} column(s) to {type_convert_target}")

    # Missing values
    targets = [c for c in (missing_columns or df.columns.tolist()) if c in df.columns]
    if missing_strategy == "drop":
        df = df.dropna(subset=targets)
        msgs.append("Dropped rows with missing values")
    elif missing_strategy in {"mean", "median"}:
        num_targets = [c for c in targets if pd.api.types.is_numeric_dtype(df[c])]
        for col in num_targets:
            fill = df[col].mean() if missing_strategy == "mean" else df[col].median()
            df[col] = df[col].fillna(fill)
        msgs.append(f"Filled numeric missing with {missing_strategy}")
    elif missing_strategy == "mode":
        for col in targets:
            m = df[col].mode(dropna=True)
            if not m.empty:
                df[col] = df[col].fillna(m.iloc[0])
        msgs.append("Filled missing with mode")
    elif missing_strategy == "ffill":
        df[targets] = df[targets].ffill()
        msgs.append("Applied forward fill")
    elif missing_strategy == "bfill":
        df[targets] = df[targets].bfill()
        msgs.append("Applied backward fill")

    # Duplicates
    if duplicate_scope == "all":
        df = df.drop_duplicates()
        msgs.append("Removed exact duplicate rows")
    elif duplicate_scope == "subset" and duplicate_subset_columns:
        sub = [c for c in duplicate_subset_columns if c in df.columns]
        if sub:
            df = df.drop_duplicates(subset=sub)
            msgs.append(f"Removed duplicates on {len(sub)} columns")

    # Drop columns
    if drop_columns:
        to_drop = [c for c in drop_columns if c in df.columns]
        if to_drop:
            df = df.drop(columns=to_drop)
            msgs.append(f"Dropped {len(to_drop)} column(s)")

    # Row filter
    if row_filter_query:
        try:
            df = df.query(row_filter_query)
            msgs.append("Applied row filter")
        except Exception as e:
            return _make_table(df), _err(f"Filter error: {e}"), no_update

    # Outliers
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    ol_targets = [c for c in (outlier_columns or numeric_cols) if c in numeric_cols]
    if outlier_mode == "remove" and ol_targets:
        keep = pd.Series([True]*len(df), index=df.index)
        for col in ol_targets:
            std = df[col].std()
            if pd.isna(std) or std == 0: continue
            z = (df[col] - df[col].mean()) / std
            keep &= z.abs() <= threshold
        df = df[keep]
        msgs.append(f"Removed outlier rows (Z > {threshold})")
    elif outlier_mode == "cap" and ol_targets:
        for col in ol_targets:
            std = df[col].std()
            if pd.isna(std) or std == 0: continue
            lo = df[col].mean() - threshold*std
            hi = df[col].mean() + threshold*std
            df[col] = df[col].clip(lower=lo, upper=hi)
        msgs.append(f"Capped outlier values (Z > {threshold})")

    df = df.reset_index(drop=True)
    ser = _serialize_df(df)
    after = len(df)
    summary = f"✓ {before:,} → {after:,} rows.  " + "  |  ".join(msgs) if msgs else f"✓ No changes applied. {before:,} rows unchanged."
    updated = {"filename": active.get("filename", "dataset"), "records": ser.to_dict("records"), "cleaning_applied": True}
    return _make_table(ser), _ok(summary), updated


@dash.callback(
    Output("cleaned-csv-download", "data"),
    Input("export-cleaned-csv", "n_clicks"),
    State("shared-dataset", "data"),
    prevent_initial_call=True,
)
def export_csv(n, shared_dataset):
    if not shared_dataset or not shared_dataset.get("records"): return None
    df = pd.DataFrame(shared_dataset["records"])
    return dcc.send_data_frame(df.to_csv, "cleaned_dataset.csv", index=False)


@dash.callback(
    Output("cleaned-xlsx-download", "data"),
    Input("export-cleaned-xlsx", "n_clicks"),
    State("shared-dataset", "data"),
    prevent_initial_call=True,
)
def export_xlsx(n, shared_dataset):
    if not shared_dataset or not shared_dataset.get("records"): return None
    df = pd.DataFrame(shared_dataset["records"])
    b = dataframe_to_excel_bytes(df)
    return dcc.send_bytes(lambda s: s.write(b), "cleaned_dataset.xlsx")
