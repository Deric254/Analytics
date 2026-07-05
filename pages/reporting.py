"""
Reporting — single output: a business-oriented, fully dynamic PDF report.
Generates on button click only. No HTML/Excel exports — PDF is the deliverable.
"""
import dash
from dash import html, dcc, dash_table, Input, Output, State
import pandas as pd
import plotly.io as pio
from services.export_utils import build_report_data, report_to_pdf, _analyze_figure

dash.register_page(__name__, path="/reporting", name="Reporting")

BRAND = "#3e8865"


def _card(title, children, accent=BRAND):
    return html.Div([
        html.H4(title, style={"fontSize": "14px", "fontWeight": "700", "color": accent,
                              "borderLeft": f"3px solid {accent}", "paddingLeft": "10px",
                              "marginBottom": "12px"}),
        *children,
    ], style={"background": "#fff", "borderRadius": "10px", "padding": "18px 20px",
               "boxShadow": "0 1px 6px rgba(0,0,0,0.07)", "border": "1px solid #e5e7eb",
               "marginBottom": "16px"})


def _row(label, value, note=""):
    return html.Div([
        html.Span(label, style={"fontWeight": "600", "color": "#374151", "width": "220px",
                                "display": "inline-block", "fontSize": "13px"}),
        html.Span(value, style={"fontFamily": "monospace", "color": "#1f2937", "fontSize": "13px"}),
        html.Span(f"  {note}", style={"color": "#9ca3af", "fontSize": "11px"}) if note else "",
    ], style={"padding": "5px 0", "borderBottom": "1px solid #f3f4f6"})


def _auto_chart_label(fig_json):
    """Pull the chart's own title (set when it was auto-generated) for use as its report label."""
    try:
        fig = pio.from_json(fig_json)
        t = fig.layout.title.text if fig.layout and fig.layout.title else None
        return t or "Auto-generated chart"
    except Exception:
        return "Auto-generated chart"


layout = html.Div([
    html.H2("Reporting", style={"marginBottom": "4px", "color": "#1f2937"}),
    html.P("Generates a business-oriented PDF report — fully dynamic from your data.",
           style={"color": "#6b7280", "fontSize": "13px", "marginBottom": "20px"}),

    dcc.Store(id="rpt-store", storage_type="session"),

    html.Div([
        html.Button("📄 Generate Report", id="rpt-generate", n_clicks=0, style={
            "padding": "9px 22px", "borderRadius": "6px", "border": "none",
            "background": BRAND, "color": "#fff", "fontWeight": "700",
            "cursor": "pointer", "marginRight": "10px", "fontSize": "14px",
        }),
        html.Button("⬇ Download PDF", id="rpt-pdf", n_clicks=0, style={
            "padding": "9px 20px", "borderRadius": "6px",
            "border": f"1px solid {BRAND}", "background": "#fff", "color": BRAND,
            "cursor": "pointer", "fontWeight": "700", "fontSize": "14px",
        }),
        dcc.Download(id="rpt-dl-pdf"),
    ], style={"marginBottom": "12px"}),

    dcc.Checklist(
        id="rpt-include-charts",
        options=[{"label": " Include all charts (auto-generated + custom-built) with analyst insights", "value": "yes"}],
        value=["yes"],
        style={"fontSize": "13px", "color": "#374151", "marginBottom": "20px"},
    ),

    dcc.Loading(html.Div(id="rpt-preview"), type="circle"),
])


def _serialize(rd):
    if not rd:
        return None
    return {
        "overview":            rd["overview"],
        "findings":            rd["findings"],
        "numeric_summary":     rd["numeric_summary"].to_dict("records"),
        "categorical_summary": rd["categorical_summary"].to_dict("records"),
        "sample_rows":         rd["sample_rows"].to_dict("records"),
    }


def _deserialize(s):
    if not s:
        return None
    return {
        "overview":            s["overview"],
        "findings":            s["findings"],
        "numeric_summary":     pd.DataFrame(s["numeric_summary"]),
        "categorical_summary": pd.DataFrame(s["categorical_summary"]),
        "sample_rows":         pd.DataFrame(s["sample_rows"]),
        "charts":              s.get("charts", []),
    }


def _make_table(frame):
    if frame is None or frame.empty:
        return html.P("No data.", style={"color": "#9ca3af"})
    return dash_table.DataTable(
        data=frame.head(30).to_dict("records"),
        columns=[{"name": c, "id": c} for c in frame.columns],
        style_table={"overflowX": "auto"},
        style_header={"background": "#f3f4f6", "fontWeight": "700", "fontSize": "12px", "border": "none"},
        style_cell={"fontSize": "12px", "padding": "7px 10px"},
        style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#fafafa"}],
        page_size=15,
    )


@dash.callback(
    Output("rpt-preview", "children"),
    Output("rpt-store",   "data"),
    Input("rpt-generate", "n_clicks"),
    State("shared-dataset",     "data"),
    State("viz-custom-gallery", "data"),
    State("viz-charts-store",   "data"),
    State("rpt-include-charts", "value"),
    prevent_initial_call=True,
)
def generate(_, shared_dataset, gallery, auto_figs, include_charts):
    if not shared_dataset or not shared_dataset.get("records"):
        return html.Div("No data loaded — go to Ingestion first.",
                        style={"color": "#dc2626"}), None

    df = pd.DataFrame(shared_dataset["records"])
    fn = shared_dataset.get("filename", "dataset")
    rd = build_report_data(df, source_name=fn)
    ov, ns, cs, sr = rd["overview"], rd["numeric_summary"], rd["categorical_summary"], rd["sample_rows"]

    # Merge both sources — auto-generated dashboard charts AND everything the
    # user built and saved in the custom gallery. Nothing is dropped.
    all_charts = []
    for fj in (auto_figs or []):
        all_charts.append({"label": f"📊 {_auto_chart_label(fj)}", "fig_json": fj})
    for item in (gallery or []):
        all_charts.append({"label": f"🛠 Custom — {item.get('label', 'Chart')}", "fig_json": item["fig_json"]})

    include = bool(all_charts and include_charts and "yes" in (include_charts or []))

    layout_out = html.Div([
        # Header
        html.Div([
            html.Div([
                html.H2(f"Report — {fn}", style={"margin": "0", "color": "#1f2937"}),
                html.P(f"Generated: {ov['generated_at']}  |  Domain: {ov['domain']}",
                       style={"color": "#6b7280", "fontSize": "12px", "margin": "4px 0 0"}),
            ]),
            html.Div([
                html.Div(f"{ov['rows']:,}", style={"fontSize": "28px", "fontWeight": "700", "color": BRAND}),
                html.Div("rows", style={"fontSize": "12px", "color": "#6b7280"}),
            ], style={"textAlign": "right"}),
        ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center",
                  "background": "#fff", "borderRadius": "10px", "padding": "20px",
                  "boxShadow": "0 1px 6px rgba(0,0,0,0.07)", "border": "1px solid #e5e7eb",
                  "marginBottom": "16px"}),

        # Overview
        _card("Dataset Overview", [
            _row("Rows",          f"{ov['rows']:,}"),
            _row("Columns",       f"{ov['columns']}",
                 f"{ov['numeric_cols']} numeric, {ov['cat_cols']} categorical, {ov['date_cols']} date"),
            _row("Missing values", f"{ov['missing']:,}", f"{100-ov['missing_pct']:.1f}% complete"),
            _row("Duplicate rows", f"{ov['duplicates']:,}"),
            _row("Key metric",    ov["value_col"]),
            _row("Main groups",   ov["group_cols"]),
        ]),

        # Executive findings — this IS the business intelligence
        _card("Executive Findings", [
            html.Div([
                html.P(f, style={"margin": "0 0 10px", "fontSize": "13.5px",
                                 "lineHeight": "1.65", "color": "#374151",
                                 "borderLeft": f"3px solid {BRAND}", "paddingLeft": "10px"})
                for f in rd["findings"]
            ])
        ]),

        _card("Numeric Column Statistics", [_make_table(ns)]) if not ns.empty else html.Div(),
        _card("Categorical Column Statistics", [_make_table(cs)]) if not cs.empty else html.Div(),

        # Charts preview — mirrors exactly what goes into the PDF, insight included
        _card(f"📊 Visual Analysis Included in PDF ({len(all_charts)} charts)", [
            html.Div([
                html.Div([
                    html.Div(item["label"], style={"fontSize": "12px", "fontWeight": "700",
                                                     "color": "#374151", "marginBottom": "6px"}),
                    dcc.Graph(id={"type": "rpt-gallery-graph", "uid": f"{i}-{item['label']}"},
                              figure=pio.from_json(item["fig_json"]),
                              config={"displaylogo": False}, style={"height": "260px"}),
                    html.Div([
                        html.Span("ANALYST INSIGHT  ", style={"fontSize": "10.5px", "fontWeight": "700", "color": BRAND}),
                        html.Span(_analyze_figure(item["fig_json"]), style={"fontSize": "11.5px", "color": "#374151"}),
                    ], style={"marginTop": "8px", "padding": "8px 10px", "background": "#f8fafb",
                              "borderRadius": "6px", "borderLeft": f"3px solid {BRAND}"}),
                ], style={"background": "#fff", "border": "1px solid #e5e7eb", "borderRadius": "8px",
                          "padding": "10px"})
                for i, item in enumerate(all_charts)
            ], style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(340px, 1fr))",
                       "gap": "14px"})
        ]) if include else html.Div(),

        _card("Sample Records (first 20)", [_make_table(sr)]),
    ])

    serialized = _serialize(rd)
    if serialized is not None:
        serialized["charts"] = all_charts if include else []

    return layout_out, serialized


@dash.callback(
    Output("rpt-dl-pdf", "data"),
    Input("rpt-pdf",     "n_clicks"),
    State("rpt-store",   "data"),
    prevent_initial_call=True,
)
def dl_pdf(_, store):
    rd = _deserialize(store)
    if not rd:
        return None

    pdf_bytes = report_to_pdf(rd)

    import re
    from datetime import datetime
    raw_name = rd.get("overview", {}).get("source", "dataset")
    base_name = str(raw_name).split("  ")[0]
    base_name = re.sub(r"\.(csv|xlsx|xls|json|db|sqlite)$", "", base_name, flags=re.IGNORECASE)
    clean_name = re.sub(r"[^A-Za-z0-9_-]+", "_", base_name).strip("_") or "dataset"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"dericbi_report_{clean_name}_{timestamp}.pdf"

    return dcc.send_bytes(lambda s: s.write(pdf_bytes), filename)
