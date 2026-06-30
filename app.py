import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import os
from flask import request
from config.settings import DERICBI_LOGO, DERICBI_SLOGAN
from services.sample_data import get_sample_dataset

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)
server = app.server

NAV_LINKS = [
    ("🏠 Dashboard",     "/"),
    ("📥 Ingestion",     "/ingestion"),
    ("🧹 Cleaning",      "/cleaning"),
    ("🔭 Exploration",   "/exploration"),
    ("📊 Visualization", "/visualization"),
    ("💡 Insights",      "/insights"),
    ("📄 Reporting",     "/reporting"),
]

sidebar = html.Div([
    html.Div([
        html.Div("DericBI", style={
            "fontSize": "22px", "fontWeight": "800", "color": "#fff",
            "letterSpacing": "-0.5px",
        }),
        html.Div("Analytics Engine", style={
            "fontSize": "11px", "color": "rgba(255,255,255,0.6)", "marginTop": "2px",
        }),
    ], style={
        "marginBottom": "28px", "paddingBottom": "16px",
        "borderBottom": "1px solid rgba(255,255,255,0.15)",
    }),

    html.Nav([
        dcc.Link(
            html.Div(label, id=f"nav-{href.strip('/') or 'home'}", style={
                "padding": "9px 14px", "borderRadius": "8px",
                "fontSize": "13.5px", "fontWeight": "500",
                "color": "rgba(255,255,255,0.88)", "cursor": "pointer",
                "marginBottom": "2px", "transition": "background 0.15s",
            }),
            href=href,
            style={"textDecoration": "none", "display": "block"},
        )
        for label, href in NAV_LINKS
    ]),

    # Sample data badge
    html.Div(id="sidebar-data-badge", style={
        "position": "absolute", "bottom": "50px", "left": "12px", "right": "12px",
    }),

    html.Div(
        DERICBI_SLOGAN,
        style={
            "position": "absolute", "bottom": "20px", "left": "20px", "right": "20px",
            "fontSize": "11px", "color": "rgba(255,255,255,0.35)", "fontStyle": "italic",
        },
    ),
], style={
    "position": "fixed", "top": 0, "left": 0, "bottom": 0, "width": "200px",
    "background": "linear-gradient(160deg, #3e8865 0%, #2d6649 100%)",
    "padding": "24px 12px", "zIndex": 1000, "overflowY": "auto",
})

content = html.Div(
    [dash.page_container],
    style={
        "marginLeft": "200px",
        "padding": "28px 32px",
        "minHeight": "100vh",
        "background": "#f8fafb",
    },
)

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    # Use localStorage so data survives page refresh within same session
    dcc.Store(id="shared-dataset",       storage_type="local"),
    dcc.Store(id="shared-visual-config", storage_type="session"),
    # Custom chart gallery — global so it's never recreated/reset by page navigation
    dcc.Store(id="viz-custom-gallery",   storage_type="session", data=[]),
    # Trigger that fires once on page load to seed sample data
    dcc.Store(id="app-initialized",      storage_type="session", data=False),
    sidebar,
    content,
], style={"fontFamily": "'Segoe UI', Roboto, Arial, sans-serif", "margin": 0, "padding": 0})


# ── Seed sample data on first load ────────────────────────────────────────────

@app.callback(
    Output("shared-dataset",    "data"),
    Output("app-initialized",   "data"),
    Output("sidebar-data-badge","children"),
    Input("app-initialized",    "data"),
    State("shared-dataset",     "data"),
    prevent_initial_call='initial_duplicate',
)
def initialize(initialized, existing_dataset):
    # If already initialized this session, do nothing
    if initialized:
        badge = _make_badge(existing_dataset)
        return dash.no_update, True, badge

    # If user already has real data loaded, keep it
    if existing_dataset and existing_dataset.get("records") and not existing_dataset.get("is_sample"):
        return dash.no_update, True, _make_badge(existing_dataset)

    # Load sample data
    sample = get_sample_dataset()
    return sample, True, _make_badge(sample)


def _make_badge(dataset):
    if not dataset or not dataset.get("records"):
        return html.Div("No data loaded",
                        style={"fontSize": "10px", "color": "rgba(255,255,255,0.4)",
                               "textAlign": "center"})
    n    = len(dataset["records"])
    fn   = dataset.get("filename", "dataset")
    name = fn.split("  ")[0] if "  " in fn else fn
    is_s = dataset.get("is_sample", False)
    return html.Div([
        html.Div("● " + ("DEMO DATA" if is_s else "YOUR DATA"),
                 style={"fontSize": "9px", "fontWeight": "700",
                        "color": "#facc15" if is_s else "#86efac",
                        "letterSpacing": "1px", "marginBottom": "2px"}),
        html.Div(name[:22], style={"fontSize": "10px", "color": "rgba(255,255,255,0.6)",
                                    "overflow": "hidden", "whiteSpace": "nowrap",
                                    "textOverflow": "ellipsis"}),
        html.Div(f"{n:,} rows", style={"fontSize": "9px", "color": "rgba(255,255,255,0.4)"}),
    ], style={"background": "rgba(0,0,0,0.2)", "borderRadius": "6px",
               "padding": "6px 8px", "textAlign": "center"})


@server.route("/ping")
def ping():
    return "pong", 200


if __name__ == "__main__":
    host  = os.getenv("HOST",  "0.0.0.0")
    port  = int(os.getenv("PORT", "10000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    print(f"\n  DericBI running → http://{host}:{port}\n")
    app.run(host=host, port=port, debug=debug)
