"""
Reporting — single output: a business-oriented, fully dynamic PDF report.
Generates on button click only. No HTML/Excel exports — PDF is the deliverable.
"""
import dash
from dash import html, dcc, dash_table, Input, Output, State
import pandas as pd
import plotly.io as pio
from services.export_utils import build_report_data, report_to_pdf, figures_to_pdf

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


layout = html.Div([
    html.H2("Reporting", style={"marginBottom": "4px", "color": "#1f2937"}),
    html.P("Generates a business-oriented PDF report — fully dynamic from your data.",
           style={"color": "#6b7280", "fontSize": "13px", "marginBottom": "20px"}),

    dcc.Store(id="rpt-store", storage_type="session"),
    # Reads the chart gallery built on the Visualization page — never created or modified here
    dcc.Store(id="viz-custom-gallery", storage_type="session", data=[]),

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
        options=[{"label": " Include charts from Visualization gallery in the PDF", "value": "yes"}],
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
        "gallery":             s.get("gallery", []),
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
    State("rpt-include-charts", "value"),
    prevent_initial_call=True,
)
def generate(_, shared_dataset, gallery, include_charts):
    if not shared_dataset or not shared_dataset.get("records"):
        return html.Div("No data loaded — go to Ingestion first.",
                        style={"color": "#dc2626"}), None

    df = pd.DataFrame(shared_dataset["records"])
    fn = shared_dataset.get("filename", "dataset")
    rd = build_report_data(df, source_name=fn)
    ov, ns, cs, sr = rd["overview"], rd["numeric_summary"], rd["categorical_summary"], rd["sample_rows"]

    include = bool(gallery and include_charts and "yes" in (include_charts or []))

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

        # Charts preview — mirrors exactly what goes into the PDF
        _card(f"📊 Charts Included in PDF ({len(gallery or [])})", [
            html.Div([
                dcc.Graph(figure=pio.from_json(item["fig_json"]),
                          config={"displaylogo": False}, style={"height": "280px"})
                for item in (gallery or [])
            ], style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(300px, 1fr))",
                       "gap": "12px"})
        ]) if include else html.Div(),

        _card("Sample Records (first 20)", [_make_table(sr)]),
    ])

    serialized = _serialize(rd)
    if serialized is not None:
        serialized["gallery"] = gallery if include else []

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

    gallery = rd.get("gallery", [])
    if gallery:
        from pypdf import PdfWriter, PdfReader
        import io

        chart_pdf_bytes = figures_to_pdf([g["fig_json"] for g in gallery], title="Charts")
        writer = PdfWriter()
        for src_bytes in (pdf_bytes, chart_pdf_bytes):
            reader = PdfReader(io.BytesIO(src_bytes))
            for page in reader.pages:
                writer.add_page(page)
        merged = io.BytesIO()
        writer.write(merged)
        pdf_bytes = merged.getvalue()

    return dcc.send_bytes(lambda s: s.write(pdf_bytes), "dericbi_report.pdf")
