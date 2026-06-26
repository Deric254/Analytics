"""
Reporting page — professional auto-report. Only generates on button click.
Includes a real executive summary section with business-language findings.
"""
import dash
from dash import html, dcc, dash_table, Input, Output, State, ctx
import pandas as pd
import numpy as np
from services.export_utils import report_data_to_html, report_data_to_pdf_bytes, build_exhaustive_report_data

dash.register_page(__name__, path="/reporting", name="Reporting")

layout = html.Div([
    html.H2("Reporting", style={"marginBottom": "4px", "color": "#1f2937"}),
    html.P("Generate a professional report from your dataset with one click.",
           style={"color": "#6b7280", "marginBottom": "20px", "fontSize": "13px"}),

    dcc.Store(id="report-data-store", storage_type="session"),

    html.Div([
        html.Button("📄 Generate Report", id="generate-report", n_clicks=0, style={
            "padding": "9px 22px", "borderRadius": "6px", "border": "none",
            "background": "#3e8865", "color": "#fff", "fontWeight": "700",
            "cursor": "pointer", "marginRight": "10px", "fontSize": "14px",
        }),
        html.Button("⬇ Export HTML", id="export-report-html", n_clicks=0, style={
            "padding": "9px 16px", "borderRadius": "6px",
            "border": "1px solid #3e8865", "background": "#fff", "color": "#3e8865",
            "cursor": "pointer", "fontWeight": "600", "marginRight": "8px",
        }),
        html.Button("⬇ Export PDF", id="export-report-pdf", n_clicks=0, style={
            "padding": "9px 16px", "borderRadius": "6px",
            "border": "1px solid #3e8865", "background": "#fff", "color": "#3e8865",
            "cursor": "pointer", "fontWeight": "600",
        }),
        dcc.Download(id="report-html-download"),
        dcc.Download(id="report-pdf-download"),
    ], style={"marginBottom": "20px"}),

    dcc.Loading(
        html.Div(id="report-preview"),
        type="circle",
    ),
])


def _coerce(df):
    out = df.copy()
    for col in out.select_dtypes(include="object").columns:
        c = pd.to_numeric(out[col], errors="coerce")
        if c.notna().mean() >= 0.8:
            out[col] = c
    return out


def _fmt(v):
    if pd.isna(v): return "N/A"
    if isinstance(v, (float, np.floating)):
        if abs(v) >= 1_000_000: return f"{v/1_000_000:,.2f}M"
        if abs(v) >= 1_000:     return f"{v:,.2f}"
        return f"{v:.4g}"
    if isinstance(v, (int, np.integer)): return f"{int(v):,}"
    return str(v)


def _detect_dates(df):
    found = []
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            found.append(col)
        elif df[col].dtype == object:
            p = pd.to_datetime(df[col], errors="coerce")
            if p.notna().mean() >= 0.6:
                found.append(col)
    return found


def _section(title, children, accent="#3e8865"):
    return html.Div([
        html.H4(title, style={
            "fontSize": "15px", "fontWeight": "700", "color": accent,
            "borderLeft": f"3px solid {accent}", "paddingLeft": "10px",
            "marginBottom": "12px",
        }),
        *children,
    ], style={
        "background": "#fff", "borderRadius": "10px", "padding": "18px 20px",
        "boxShadow": "0 1px 6px rgba(0,0,0,0.07)", "border": "1px solid #e5e7eb",
        "marginBottom": "16px",
    })


def _stat_row(label, value, note=""):
    return html.Div([
        html.Span(label, style={"fontWeight": "600", "color": "#374151", "width": "220px", "display": "inline-block", "fontSize": "13px"}),
        html.Span(value, style={"fontFamily": "monospace", "color": "#1f2937", "fontSize": "13px"}),
        html.Span(f"  {note}", style={"color": "#9ca3af", "fontSize": "11px"}) if note else "",
    ], style={"padding": "5px 0", "borderBottom": "1px solid #f3f4f6"})


def _build_executive_summary(df, filename):
    """Auto-generate business-language findings."""
    rows, cols = df.shape
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(exclude="number").columns.tolist()
    missing = int(df.isna().sum().sum())
    dups = int(df.duplicated().sum())
    date_cols = _detect_dates(df)

    findings = []

    # Data size
    findings.append(f"This dataset contains {rows:,} records across {cols} columns ({len(numeric_cols)} numeric, {len(cat_cols)} categorical).")

    # Completeness
    pct_complete = 100 * (rows*cols - missing) / max(rows*cols, 1)
    if missing == 0:
        findings.append("The dataset is fully complete with no missing values.")
    else:
        worst_col = df.isna().sum().idxmax()
        findings.append(f"Data completeness is {pct_complete:.1f}%. The column with the most gaps is '{worst_col}' ({int(df[worst_col].isna().sum()):,} missing values).")

    if dups > 0:
        findings.append(f"⚠️ {dups:,} duplicate rows detected ({100*dups/rows:.1f}% of records). Consider removing them on the Cleaning page.")

    # Numeric highlights
    for col in numeric_cols[:3]:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty: continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        outliers = int(((s < q1 - 1.5*iqr) | (s > q3 + 1.5*iqr)).sum())
        skew = float(s.skew())
        sk_text = "right-skewed (most values are low, a few very high)" if skew > 0.5 else \
                  "left-skewed (most values are high, a few very low)" if skew < -0.5 else "normally distributed"
        findings.append(
            f"Column '{col}': total {_fmt(s.sum())}, average {_fmt(s.mean())}, range {_fmt(s.min())} – {_fmt(s.max())}. "
            f"Distribution is {sk_text}."
            + (f" {outliers:,} outlier(s) detected." if outliers else "")
        )

    # Trend
    if date_cols and numeric_cols:
        dc, nc = date_cols[0], numeric_cols[0]
        tmp = df.copy()
        tmp[dc] = pd.to_datetime(tmp[dc], errors="coerce")
        tmp = tmp.dropna(subset=[dc, nc]).sort_values(dc)
        if len(tmp) >= 4:
            n = max(len(tmp)//4, 1)
            first = pd.to_numeric(tmp[nc].iloc[:n], errors="coerce").mean()
            last  = pd.to_numeric(tmp[nc].iloc[-n:], errors="coerce").mean()
            if pd.notna(first) and pd.notna(last) and first != 0:
                chg = (last - first) / abs(first) * 100
                arrow = "increased" if chg > 0 else "decreased"
                findings.append(f"Trend: '{nc}' has {arrow} by {abs(chg):.1f}% from the earliest to the most recent records.")

    # Top category
    good_cats = [c for c in cat_cols if 2 <= df[c].nunique() <= 30]
    if good_cats and numeric_cols:
        cc = good_cats[0]
        nc = numeric_cols[0]
        agg = df.groupby(cc, dropna=False)[nc].sum().sort_values(ascending=False)
        if not agg.empty:
            top_val = agg.index[0]
            top_share = 100 * agg.iloc[0] / agg.sum() if agg.sum() else 0
            findings.append(f"Top performer: '{top_val}' in '{cc}' accounts for {top_share:.1f}% of total {nc}.")

    return findings


def _build_report_layout(df, filename):
    df = _coerce(df)
    rows, cols_count = df.shape
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(exclude="number").columns.tolist()
    missing = int(df.isna().sum().sum())
    dups = int(df.duplicated().sum())
    from datetime import datetime

    findings = _build_executive_summary(df, filename)

    # Numeric stats table
    num_rows = []
    for col in numeric_cols[:10]:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty: continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        outliers = int(((s < q1 - 1.5*iqr) | (s > q3 + 1.5*iqr)).sum())
        num_rows.append({
            "Column": col,
            "Count": f"{len(s):,}",
            "Mean": _fmt(s.mean()),
            "Median": _fmt(s.median()),
            "Std Dev": _fmt(s.std()),
            "Min": _fmt(s.min()),
            "Max": _fmt(s.max()),
            "Outliers": str(outliers),
        })
    num_df = pd.DataFrame(num_rows)

    # Categorical stats table
    cat_rows = []
    for col in cat_cols[:10]:
        s = df[col].dropna().astype(str)
        vc = s.value_counts()
        cat_rows.append({
            "Column": col,
            "Unique Values": f"{s.nunique():,}",
            "Top Value": vc.index[0] if not vc.empty else "—",
            "Top Count": f"{int(vc.iloc[0]):,}" if not vc.empty else "—",
            "Missing": f"{int(df[col].isna().sum()):,}",
        })
    cat_df = pd.DataFrame(cat_rows)

    # Sample rows
    sample_df = df.head(15)

    return html.Div([
        # Header
        html.Div([
            html.Div([
                html.H2("Dataset Analysis Report", style={"margin": "0", "color": "#1f2937"}),
                html.P(f"Source: {filename}  |  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                       style={"color": "#6b7280", "fontSize": "12px", "margin": "4px 0 0"}),
            ]),
            html.Div([
                html.Div(f"{rows:,}", style={"fontSize": "28px", "fontWeight": "700", "color": "#3e8865"}),
                html.Div("rows", style={"fontSize": "12px", "color": "#6b7280"}),
            ], style={"textAlign": "right"}),
        ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center",
                  "background": "#fff", "borderRadius": "10px", "padding": "20px",
                  "boxShadow": "0 1px 6px rgba(0,0,0,0.07)", "border": "1px solid #e5e7eb",
                  "marginBottom": "16px"}),

        # Executive summary
        _section("Executive Summary", [
            html.Div([
                html.P(f, style={"margin": "0 0 8px", "fontSize": "13.5px", "lineHeight": "1.6", "color": "#374151"})
                for f in findings
            ])
        ], accent="#3e8865"),

        # Dataset overview
        _section("Dataset Overview", [
            _stat_row("Total rows",          f"{rows:,}"),
            _stat_row("Total columns",       f"{cols_count}",      f"{len(numeric_cols)} numeric, {len(cat_cols)} categorical"),
            _stat_row("Missing values",      f"{missing:,}",       f"{100*(rows*cols_count-missing)/max(rows*cols_count,1):.1f}% complete"),
            _stat_row("Duplicate rows",      f"{dups:,}"),
            _stat_row("Columns",             ", ".join(df.columns.tolist()[:12]) + ("…" if len(df.columns) > 12 else "")),
        ]),

        # Numeric summary
        _section("Numeric Column Statistics", [
            dash_table.DataTable(
                data=num_df.to_dict("records") if not num_df.empty else [],
                columns=[{"name": c, "id": c} for c in num_df.columns] if not num_df.empty else [],
                style_table={"overflowX": "auto"},
                style_header={"background": "#f3f4f6", "fontWeight": "700", "fontSize": "12px", "border": "none"},
                style_cell={"fontSize": "12px", "padding": "7px 10px"},
                style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#fafafa"}],
            ) if not num_df.empty else html.P("No numeric columns.", style={"color": "#9ca3af"}),
        ]) if numeric_cols else html.Div(),

        # Categorical summary
        _section("Categorical Column Statistics", [
            dash_table.DataTable(
                data=cat_df.to_dict("records") if not cat_df.empty else [],
                columns=[{"name": c, "id": c} for c in cat_df.columns] if not cat_df.empty else [],
                style_table={"overflowX": "auto"},
                style_header={"background": "#f3f4f6", "fontWeight": "700", "fontSize": "12px", "border": "none"},
                style_cell={"fontSize": "12px", "padding": "7px 10px"},
                style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#fafafa"}],
            ) if not cat_df.empty else html.P("No categorical columns.", style={"color": "#9ca3af"}),
        ]) if cat_cols else html.Div(),

        # Sample data
        _section("Sample Records (first 15 rows)", [
            dash_table.DataTable(
                data=sample_df.to_dict("records"),
                columns=[{"name": c, "id": c} for c in sample_df.columns],
                style_table={"overflowX": "auto"},
                style_header={"background": "#f3f4f6", "fontWeight": "700", "fontSize": "12px", "border": "none"},
                style_cell={"fontSize": "11px", "padding": "6px 8px"},
                style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#fafafa"}],
                page_size=15,
            ),
        ]),
    ])


def _serialize_report(report_data):
    if not report_data: return None
    return {
        "overview": report_data["overview"],
        "numeric_summary": report_data["numeric_summary"].to_dict("records"),
        "categorical_summary": report_data["categorical_summary"].to_dict("records"),
        "sample_rows": report_data["sample_rows"].to_dict("records"),
    }


def _deserialize_report(s):
    if not s: return None
    return {
        "overview": s.get("overview", {}),
        "numeric_summary": pd.DataFrame(s.get("numeric_summary", [])),
        "categorical_summary": pd.DataFrame(s.get("categorical_summary", [])),
        "sample_rows": pd.DataFrame(s.get("sample_rows", [])),
    }


@dash.callback(
    Output("report-preview", "children"),
    Output("report-data-store", "data"),
    Input("generate-report", "n_clicks"),
    State("shared-dataset", "data"),
    prevent_initial_call=True,
)
def generate_report(n_clicks, shared_dataset):
    if not n_clicks:
        return "", None
    if not shared_dataset or not shared_dataset.get("records"):
        return html.Div("No data loaded. Go to Ingestion first.", style={"color": "#dc2626"}), None
    df = pd.DataFrame(shared_dataset["records"])
    filename = shared_dataset.get("filename", "dataset")
    layout_component = _build_report_layout(df, filename)
    report_data = build_exhaustive_report_data(_coerce(df), source_name=filename)
    return layout_component, _serialize_report(report_data)


@dash.callback(
    Output("report-html-download", "data"),
    Input("export-report-html", "n_clicks"),
    State("report-data-store", "data"),
    prevent_initial_call=True,
)
def export_html(n, store):
    rd = _deserialize_report(store)
    if not rd: return None
    return dict(content=report_data_to_html(rd), filename="dericbi_report.html", type="text/html")


@dash.callback(
    Output("report-pdf-download", "data"),
    Input("export-report-pdf", "n_clicks"),
    State("report-data-store", "data"),
    prevent_initial_call=True,
)
def export_pdf(n, store):
    rd = _deserialize_report(store)
    if not rd: return None
    b = report_data_to_pdf_bytes(rd)
    return dcc.send_bytes(lambda s: s.write(b), "dericbi_report.pdf")
