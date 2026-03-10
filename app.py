import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import os
import threading
import time
import requests as req
from flask import request, redirect
from config.settings import DERICBI_LOGO, DERICBI_SLOGAN

# Initialize Dash app with Bootstrap for premium styling
app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.CYBORG],
    suppress_callback_exceptions=True
)
server = app.server

# ── Self keep-alive — pings own /ping every 10 minutes so Render never sleeps ─
def _keep_alive():
    """Runs in background thread. Pings this app every 10 min to prevent sleep."""
    # Wait 60s after startup before first ping so app is fully ready
    time.sleep(60)
    port = int(os.getenv("PORT", "10000"))
    url  = f"http://0.0.0.0:{port}/ping"
    while True:
        try:
            req.get(url, timeout=10)
        except Exception:
            pass  # silently ignore — app may be busy, next ping will succeed
        time.sleep(600)  # ping every 10 minutes

threading.Thread(target=_keep_alive, daemon=True).start()

# ── Ping endpoint — lightweight health check ──────────────────────────────────
@server.route("/ping")
def ping():
    return "pong", 200

# Sidebar navigation
sidebar = html.Div(
    [
        html.Img(
            src=DERICBI_LOGO,
            alt="DericBI Logo",
            style={"height": "48px", "width": "auto", "marginBottom": "0.75rem"},
        ),
        html.H2("DericBI", className="display-6"),
        html.Hr(),
        html.P(DERICBI_SLOGAN, className="lead"),
        dbc.Nav(
            [
                dbc.NavLink("Ingestion",     href="/ingestion",     active="exact"),
                dbc.NavLink("Cleaning",      href="/cleaning",      active="exact"),
                dbc.NavLink("Exploration",   href="/exploration",   active="exact"),
                dbc.NavLink("Visualization", href="/visualization", active="exact"),
                dbc.NavLink("Insights",      href="/insights",      active="exact"),
                dbc.NavLink("Reporting",     href="/reporting",     active="exact"),
            ],
            className="analytics-sidebar-nav",
            vertical=True,
            pills=True,
        ),
    ],
    className="analytics-sidebar",
    id="sidebar",
    style={
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "16rem",
        "padding": "2rem 1rem",
        "backgroundColor": "#3e8865",
        "color": "#ffffff"
    },
)

# Overlay for mobile sidebar
sidebar_overlay = html.Div(id="sidebar-overlay", className="sidebar-overlay")

# Top header
header = html.Div(
    [
        html.Div(
            [
                html.Button("☰", id="mobile-menu-btn", className="mobile-menu-toggle", n_clicks=0),
            ],
            className="analytics-header-left",
        ),
        html.H4("DericBI Analytics Engine", className="analytics-header-title mb-0"),
        html.Div(
            [
                html.A(
                    html.Button(
                        "🏠 Home",
                        style={
                            "background": "#facc15",
                            "color": "#1f2937",
                            "border": "none",
                            "borderRadius": "6px",
                            "padding": "6px 14px",
                            "fontWeight": "600",
                            "cursor": "pointer",
                            "marginRight": "12px",
                            "fontSize": "14px",
                        },
                    ),
                    href="https://dericbi.vercel.app",
                    target="_blank",
                    rel="noopener noreferrer",
                ),
                html.Img(
                    src=DERICBI_LOGO,
                    alt="DericBI Logo",
                    style={"height": "26px", "width": "auto", "marginRight": "8px"},
                ),
                html.Small(DERICBI_SLOGAN),
            ],
            className="analytics-header-right",
        ),
    ],
    className="analytics-header",
    style={
        "position": "fixed",
        "top": 0,
        "left": "16rem",
        "right": 0,
        "height": "64px",
        "padding": "0 1.25rem",
        "backgroundColor": "#3e8865",
        "color": "#ffffff",
        "borderBottom": "1px solid rgba(250, 204, 21, 0.45)",
        "zIndex": 1000,
    },
)

# Content area
content = html.Div(
    [
        dash.page_container
    ],
    style={
        "marginLeft": "18rem",
        "marginRight": "2rem",
        "marginTop": "80px",
        "padding": "1rem"
    },
)

# App layout
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="shared-dataset",      storage_type="session"),
    dcc.Store(id="shared-visual-config", storage_type="session"),
    dcc.Store(id="sidebar-state",       data={"open": False}),
    sidebar_overlay,
    sidebar,
    header,
    content
])


@server.before_request
def ensure_default_route():
    if request.path == "/":
        return redirect("/ingestion", code=302)
    return None


@app.callback(
    [Output("sidebar", "className"), Output("sidebar-overlay", "className")],
    [Input("mobile-menu-btn", "n_clicks"), Input("sidebar-overlay", "n_clicks")],
    [State("sidebar-state", "data")],
    prevent_initial_call=True
)
def toggle_sidebar(menu_clicks, overlay_clicks, state):
    is_open = state.get("open", False)
    new_state = not is_open
    sidebar_class  = "analytics-sidebar open" if new_state else "analytics-sidebar"
    overlay_class  = "sidebar-overlay active" if new_state else "sidebar-overlay"
    return sidebar_class, overlay_class


if __name__ == "__main__":
    host  = os.getenv("HOST",  "0.0.0.0")
    port  = int(os.getenv("PORT", "10000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)
