"""
Reporting — professional auto-report. Generate on button click only.
Executive findings in plain language, export HTML and PDF.
"""
import dash
from dash import html, dcc, dash_table, Input, Output, State, ctx
import pandas as pd
import numpy as np
from services.export_utils import (
    build_report_data, report_to_html, report_to_pdf, df_to_excel
)

dash.register_page(__name__, path="/reporting", name="Reporting")

BRAND = "#3e8865"

def _card(title, children, accent=BRAND):
    return html.Div([
        html.H4(title, style={"fontSize":"14px","fontWeight":"700","color":accent,
                              "borderLeft":f"3px solid {accent}","paddingLeft":"10px",
                              "marginBottom":"12px"}),
        *children,
    ], style={"background":"#fff","borderRadius":"10px","padding":"18px 20px",
               "boxShadow":"0 1px 6px rgba(0,0,0,0.07)","border":"1px solid #e5e7eb",
               "marginBottom":"16px"})

def _row(label, value, note=""):
    return html.Div([
        html.Span(label, style={"fontWeight":"600","color":"#374151","width":"220px",
                                "display":"inline-block","fontSize":"13px"}),
        html.Span(value, style={"fontFamily":"monospace","color":"#1f2937","fontSize":"13px"}),
        html.Span(f"  {note}", style={"color":"#9ca3af","fontSize":"11px"}) if note else "",
    ], style={"padding":"5px 0","borderBottom":"1px solid #f3f4f6"})

layout = html.Div([
    html.H2("Reporting", style={"marginBottom":"4px","color":"#1f2937"}),
    html.P("Auto-generates a professional report with executive findings in plain language.",
           style={"color":"#6b7280","fontSize":"13px","marginBottom":"20px"}),

    dcc.Store(id="rpt-store", storage_type="session"),

    html.Div([
        html.Button("📄 Generate Report", id="rpt-generate", n_clicks=0, style={
            "padding":"9px 22px","borderRadius":"6px","border":"none",
            "background":BRAND,"color":"#fff","fontWeight":"700",
            "cursor":"pointer","marginRight":"10px","fontSize":"14px",
        }),
        html.Button("⬇ HTML", id="rpt-html", n_clicks=0, style={
            "padding":"9px 16px","borderRadius":"6px",
            "border":f"1px solid {BRAND}","background":"#fff","color":BRAND,
            "cursor":"pointer","fontWeight":"600","marginRight":"8px",
        }),
        html.Button("⬇ PDF", id="rpt-pdf", n_clicks=0, style={
            "padding":"9px 16px","borderRadius":"6px",
            "border":f"1px solid {BRAND}","background":"#fff","color":BRAND,
            "cursor":"pointer","fontWeight":"600","marginRight":"8px",
        }),
        html.Button("⬇ Excel", id="rpt-excel", n_clicks=0, style={
            "padding":"9px 16px","borderRadius":"6px",
            "border":f"1px solid {BRAND}","background":"#fff","color":BRAND,
            "cursor":"pointer","fontWeight":"600",
        }),
        dcc.Download(id="rpt-dl-html"),
        dcc.Download(id="rpt-dl-pdf"),
        dcc.Download(id="rpt-dl-excel"),
    ], style={"marginBottom":"20px"}),

    dcc.Loading(html.Div(id="rpt-preview"), type="circle"),
])


def _serialize(rd):
    if not rd: return None
    return {
        "overview":              rd["overview"],
        "findings":              rd["findings"],
        "numeric_summary":       rd["numeric_summary"].to_dict("records"),
        "categorical_summary":   rd["categorical_summary"].to_dict("records"),
        "sample_rows":           rd["sample_rows"].to_dict("records"),
    }

def _deserialize(s):
    if not s: return None
    return {
        "overview":            s["overview"],
        "findings":            s["findings"],
        "numeric_summary":     pd.DataFrame(s["numeric_summary"]),
        "categorical_summary": pd.DataFrame(s["categorical_summary"]),
        "sample_rows":         pd.DataFrame(s["sample_rows"]),
    }


@dash.callback(
    Output("rpt-preview", "children"),
    Output("rpt-store",   "data"),
    Input("rpt-generate", "n_clicks"),
    State("shared-dataset","data"),
    prevent_initial_call=True,
)
def generate(_, shared_dataset):
    if not shared_dataset or not shared_dataset.get("records"):
        return html.Div("No data loaded — go to Ingestion first.",
                        style={"color":"#dc2626"}), None

    df  = pd.DataFrame(shared_dataset["records"])
    fn  = shared_dataset.get("filename", "dataset")
    rd  = build_report_data(df, source_name=fn)
    ov  = rd["overview"]
    ns  = rd["numeric_summary"]
    cs  = rd["categorical_summary"]
    sr  = rd["sample_rows"]

    def make_table(frame):
        if frame is None or frame.empty:
            return html.P("No data.", style={"color":"#9ca3af"})
        return dash_table.DataTable(
            data=frame.head(30).to_dict("records"),
            columns=[{"name":c,"id":c} for c in frame.columns],
            style_table={"overflowX":"auto"},
            style_header={"background":"#f3f4f6","fontWeight":"700","fontSize":"12px","border":"none"},
            style_cell={"fontSize":"12px","padding":"7px 10px"},
            style_data_conditional=[{"if":{"row_index":"odd"},"backgroundColor":"#fafafa"}],
            page_size=15,
        )

    layout_out = html.Div([
        # Header
        html.Div([
            html.Div([
                html.H2(f"Report — {fn}", style={"margin":"0","color":"#1f2937"}),
                html.P(f"Generated: {ov['generated_at']}  |  Domain: {ov['domain']}",
                       style={"color":"#6b7280","fontSize":"12px","margin":"4px 0 0"}),
            ]),
            html.Div([
                html.Div(f"{ov['rows']:,}", style={"fontSize":"28px","fontWeight":"700","color":BRAND}),
                html.Div("rows", style={"fontSize":"12px","color":"#6b7280"}),
            ], style={"textAlign":"right"}),
        ], style={"display":"flex","justifyContent":"space-between","alignItems":"center",
                  "background":"#fff","borderRadius":"10px","padding":"20px",
                  "boxShadow":"0 1px 6px rgba(0,0,0,0.07)","border":"1px solid #e5e7eb",
                  "marginBottom":"16px"}),

        # Overview stats
        _card("Dataset Overview", [
            _row("Rows",         f"{ov['rows']:,}"),
            _row("Columns",      f"{ov['columns']}",
                 f"{ov['numeric_cols']} numeric, {ov['cat_cols']} categorical, {ov['date_cols']} date"),
            _row("Missing values",f"{ov['missing']:,}",
                 f"{100-ov['missing_pct']:.1f}% complete"),
            _row("Duplicate rows",f"{ov['duplicates']:,}"),
            _row("Key metric",   ov['value_col']),
            _row("Main groups",  ov['group_cols']),
        ]),

        # Executive findings
        _card("Executive Findings", [
            html.Div([
                html.P(f, style={"margin":"0 0 10px","fontSize":"13.5px",
                                 "lineHeight":"1.65","color":"#374151",
                                 "borderLeft":f"3px solid {BRAND}",
                                 "paddingLeft":"10px"})
                for f in rd["findings"]
            ])
        ]),

        # Numeric summary
        _card("Numeric Column Statistics", [make_table(ns)]) if not ns.empty else html.Div(),

        # Categorical summary
        _card("Categorical Column Statistics", [make_table(cs)]) if not cs.empty else html.Div(),

        # Sample
        _card("Sample Records (first 20)", [make_table(sr)]),
    ])

    return layout_out, _serialize(rd)


@dash.callback(
    Output("rpt-dl-html","data"),
    Input("rpt-html","n_clicks"),
    State("rpt-store","data"),
    prevent_initial_call=True,
)
def dl_html(_, store):
    rd = _deserialize(store)
    if not rd: return None
    return dict(content=report_to_html(rd), filename="dericbi_report.html", type="text/html")


@dash.callback(
    Output("rpt-dl-pdf","data"),
    Input("rpt-pdf","n_clicks"),
    State("rpt-store","data"),
    prevent_initial_call=True,
)
def dl_pdf(_, store):
    rd = _deserialize(store)
    if not rd: return None
    b = report_to_pdf(rd)
    return dcc.send_bytes(lambda s: s.write(b), "dericbi_report.pdf")


@dash.callback(
    Output("rpt-dl-excel","data"),
    Input("rpt-excel","n_clicks"),
    State("shared-dataset","data"),
    prevent_initial_call=True,
)
def dl_excel(_, shared_dataset):
    if not shared_dataset or not shared_dataset.get("records"): return None
    df = pd.DataFrame(shared_dataset["records"])
    b  = df_to_excel(df)
    return dcc.send_bytes(lambda s: s.write(b), "dericbi_data.xlsx")
