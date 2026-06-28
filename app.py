import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import os
import threading
import time
import requests as req
from flask import request, redirect
from config.settings import DERICBI_LOGO, DERICBI_SLOGAN

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)
server = app.server

NAV_LINKS = [
    ("🏠 Dashboard",      "/"),
    ("📥 Ingestion",      "/ingestion"),
    ("🧹 Cleaning",       "/cleaning"),
    ("🔭 Exploration",    "/exploration"),
    ("📊 Visualization",  "/visualization"),
    ("💡 Insights",       "/insights"),
    ("📄 Reporting",      "/reporting"),
]

sidebar = html.Div([
    html.Div([
        html.Div("DericBI", style={
            "fontSize": "22px", "fontWeight": "800", "color": "#fff",
            "letterSpacing": "-0.5px",
        }),
        html.Div("Analytics Engine", style={
            "fontSize": "11px", "color": "rgba(255,255,255,0.6)", "marginTop": "2px"
        }),
    ], style={
        "marginBottom": "28px", "paddingBottom": "16px",
        "borderBottom": "1px solid rgba(255,255,255,0.15)",
    }),

    html.Nav([
        dcc.Link(
            html.Div(label, style={
                "padding": "9px 14px", "borderRadius": "8px",
                "fontSize": "13.5px", "fontWeight": "500",
                "color": "rgba(255,255,255,0.88)", "cursor": "pointer",
                "marginBottom": "2px",
            }),
            href=href,
            style={"textDecoration": "none", "display": "block"},
        )
        for label, href in NAV_LINKS
    ]),

    html.Div(
        DERICBI_SLOGAN,
        style={
            "position": "absolute", "bottom": "20px", "left": "20px", "right": "20px",
            "fontSize": "11px", "color": "rgba(255,255,255,0.35)", "fontStyle": "italic",
        }
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
    dcc.Store(id="shared-dataset",       storage_type="session"),
    dcc.Store(id="shared-visual-config", storage_type="session"),
    sidebar,
    content,
], style={"fontFamily": "'Segoe UI', Roboto, Arial, sans-serif", "margin": 0, "padding": 0})


@server.route("/ping")
def ping():
    return "pong", 200


if __name__ == "__main__":
    host  = os.getenv("HOST",  "127.0.0.1")
    port  = int(os.getenv("PORT", "10000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    print(f"\n  DericBI running → http://{host}:{port}\n")
    app.run(host=host, port=port, debug=debug)
