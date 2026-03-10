import dash
from dash import html, dcc, Input, Output, State
import pandas as pd
from services.report_generator import generate_report as build_report
from services.export_utils import report_data_to_html, report_data_to_pdf_bytes

dash.register_page(__name__, path="/reporting", name="Reporting")

layout = html.Div([
    html.H2("DericBI Analytics Engine - Reporting", className="page-title"),
    dcc.Store(id="report-data-store", storage_type="session"),

    # Report Options
    html.Div([
        html.Label("Select Report Layout"),
        dcc.RadioItems(
            id="report-layout",
            options=[
                {"label": "System Recommended Layout", "value": "system"},
                {"label": "User Customized Layout", "value": "user"}
            ],
            value="system"
        ),
        html.Button("Generate Report", id="generate-report", n_clicks=0),
        html.Button("Export Report HTML", id="export-report-html", n_clicks=0, style={"marginLeft": "8px"}),
        html.Button("Export Report PDF", id="export-report-pdf", n_clicks=0, style={"marginLeft": "8px"}),
    ], style={"marginTop": "20px"}),
    dcc.Download(id="report-html-download"),
    dcc.Download(id="report-pdf-download"),

    # Report Preview
    html.Div(id="report-preview", style={"marginTop": "20px", "border": "1px solid #ccc", "padding": "10px"})
])


def _serialize_report_data(report_data: dict | None):
    if not report_data:
        return None

    return {
        "overview": report_data["overview"],
        "numeric_summary": report_data["numeric_summary"].to_dict("records"),
        "categorical_summary": report_data["categorical_summary"].to_dict("records"),
        "sample_rows": report_data["sample_rows"].to_dict("records"),
    }


def _deserialize_report_data(serialized: dict | None):
    if not serialized:
        return None

    return {
        "overview": serialized.get("overview", {}),
        "numeric_summary": pd.DataFrame(serialized.get("numeric_summary", [])),
        "categorical_summary": pd.DataFrame(serialized.get("categorical_summary", [])),
        "sample_rows": pd.DataFrame(serialized.get("sample_rows", [])),
    }

@dash.callback(
    Output("report-preview", "children"),
    Output("report-data-store", "data"),
    Input("generate-report", "n_clicks"),
    Input("report-layout", "value"),
    State("shared-dataset", "data")
)
def generate_report(n_clicks, layout_choice, shared_dataset):
    if n_clicks > 0:
        if not shared_dataset or not shared_dataset.get("records"):
            return html.Div("No uploaded data found. Upload a dataset on the Ingestion page first."), None

        df = pd.DataFrame(shared_dataset["records"])
        filename = shared_dataset.get("filename", "uploaded dataset")
        component, report_data = build_report(df=df, layout_choice=layout_choice, source_name=filename)
        return component, _serialize_report_data(report_data)
    return "", None


@dash.callback(
    Output("report-html-download", "data"),
    Input("export-report-html", "n_clicks"),
    State("report-data-store", "data"),
    prevent_initial_call=True
)
def export_report_html(n_clicks, report_data_store):
    report_data = _deserialize_report_data(report_data_store)
    if not report_data:
        return None

    html_content = report_data_to_html(report_data)
    return dict(content=html_content, filename="dynamic_report.html", type="text/html")


@dash.callback(
    Output("report-pdf-download", "data"),
    Input("export-report-pdf", "n_clicks"),
    State("report-data-store", "data"),
    prevent_initial_call=True
)
def export_report_pdf(n_clicks, report_data_store):
    report_data = _deserialize_report_data(report_data_store)
    if not report_data:
        return None

    pdf_bytes = report_data_to_pdf_bytes(report_data)
    return dcc.send_bytes(lambda stream: stream.write(pdf_bytes), "dynamic_report.pdf")
