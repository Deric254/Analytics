import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import os
from flask import request, session, redirect
from config.settings import DERICBI_LOGO, DERICBI_SLOGAN
from services.sample_data import get_sample_dataset
from services.ai_assistant import ask as ai_ask, which_ai

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)
server = app.server
server.secret_key = os.getenv("SECRET_KEY", "dericbi-dev-secret-change-in-production")

LOGIN_ENABLED = os.getenv("LOGIN_ENABLED", "false").lower() == "true"

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
        "position": "absolute", "bottom": "78px", "left": "12px", "right": "12px",
    }),

    # Logout button — only shown when login is enabled
    html.Div(
        html.A("🚪 Log Out", href="/logout", style={
            "fontSize": "11px", "color": "rgba(255,255,255,0.55)", "textDecoration": "none",
            "fontWeight": "600",
        }),
        id="logout-link-container",
        style={
            "position": "absolute", "bottom": "50px", "left": "20px", "right": "20px",
            "display": "block" if LOGIN_ENABLED else "none",
        },
    ),

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
}, id="sidebar")

content = html.Div(
    [dash.page_container],
    id="page-content",
    style={
        "marginLeft": "200px",
        "padding": "28px 32px",
        "minHeight": "100vh",
        "background": "#f8fafb",
    },
)

# Mobile menu toggle — a tiny clientside (browser-only) callback flips a CSS
# class on #sidebar. No server round-trip, no page state, no effect on any
# existing callback or data logic — purely a UI show/hide switch.
mobile_hamburger = html.Button("☰", id="mobile-hamburger-btn", n_clicks=0, className="mobile-hamburger-label")
mobile_overlay   = html.Div(id="mobile-menu-overlay", n_clicks=0, className="mobile-menu-overlay")

# ── Floating AI Assistant ──────────────────────────────────────────────────────

ai_button = html.Div([
    # Collapsed floating button
    html.Button("✨", id="ai-toggle-btn", n_clicks=0, style={
        "position": "fixed", "bottom": "24px", "right": "24px", "zIndex": 2000,
        "width": "56px", "height": "56px", "borderRadius": "50%", "border": "none",
        "background": "linear-gradient(135deg, #3e8865, #2d6649)", "color": "#fff",
        "fontSize": "24px", "cursor": "pointer",
        "boxShadow": "0 4px 16px rgba(0,0,0,0.25)",
    }),

    # Expandable chat panel
    html.Div(id="ai-panel", children=[
        html.Div([
            html.Div([
                html.Span("✨ DericBI AI", style={"fontWeight": "700", "fontSize": "14px", "color": "#fff"}),
                html.Span(id="ai-model-badge", style={
                    "fontSize": "9px", "color": "rgba(255,255,255,0.7)", "marginLeft": "8px",
                }),
            ]),
            html.Div([
                html.Button("🗑", id="ai-clear-btn", n_clicks=0, title="Clear conversation", style={
                    "background": "none", "border": "none", "color": "rgba(255,255,255,0.85)",
                    "cursor": "pointer", "fontSize": "14px", "marginRight": "10px",
                }),
                html.Button("✕", id="ai-close-btn", n_clicks=0, style={
                    "background": "none", "border": "none", "color": "#fff", "cursor": "pointer",
                    "fontSize": "16px", "fontWeight": "700",
                }),
            ], style={"display": "flex", "alignItems": "center"}),
        ], style={
            "display": "flex", "justifyContent": "space-between", "alignItems": "center",
            "background": "linear-gradient(135deg, #3e8865, #2d6649)",
            "padding": "12px 16px", "borderRadius": "12px 12px 0 0",
        }),

        dcc.Loading(
            html.Div(id="ai-messages", style={
                "height": "320px", "overflowY": "auto", "padding": "14px",
                "background": "#f8fafb", "fontSize": "13px",
            }),
            type="dot",
        ),

        html.Div([
            dcc.Input(
                id="ai-input", type="text", placeholder="Ask about your data, or anything...",
                n_submit=0,
                style={
                    "flex": "1", "padding": "9px 12px", "border": "1px solid #d1d5db",
                    "borderRadius": "8px", "fontSize": "13px", "marginRight": "6px",
                },
            ),
            html.Button("→", id="ai-send-btn", n_clicks=0, disabled=False, style={
                "width": "36px", "height": "36px", "borderRadius": "8px", "border": "none",
                "background": "#3e8865", "color": "#fff", "cursor": "pointer", "fontWeight": "700",
            }),
        ], style={
            "display": "flex", "padding": "10px 14px", "background": "#fff",
            "borderRadius": "0 0 12px 12px", "borderTop": "1px solid #e5e7eb",
        }),
    ], style={
        "position": "fixed", "bottom": "90px", "right": "24px", "zIndex": 2000,
        "width": "340px", "background": "#fff", "borderRadius": "12px",
        "boxShadow": "0 8px 32px rgba(0,0,0,0.2)", "display": "none",
        "border": "1px solid #e5e7eb",
    }),

    dcc.Store(id="ai-panel-open", data=False),
    dcc.Store(id="ai-history",    data=[]),
])


app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="shared-dataset",       storage_type="session"),
    dcc.Store(id="shared-visual-config", storage_type="session"),
    dcc.Store(id="viz-custom-gallery",   storage_type="session", data=[]),
    dcc.Store(id="viz-charts-store",     storage_type="session", data=[]),
    dcc.Store(id="app-initialized",      storage_type="session", data=False),
    dcc.Store(id="auth-state",           storage_type="session", data=False),
    mobile_hamburger,
    mobile_overlay,
    sidebar,
    content,
    ai_button,
], style={"fontFamily": "'Segoe UI', Roboto, Arial, sans-serif", "margin": 0, "padding": 0})


# ── Active nav link highlight — pure UI, reacts to URL only ───────────────────

_NAV_IDS = [f"nav-{href.strip('/') or 'home'}" for _, href in NAV_LINKS]

@app.callback(
    [Output(nid, "style") for nid in _NAV_IDS],
    Input("url", "pathname"),
)
def highlight_active_nav(pathname):
    base_style = {
        "padding": "9px 14px", "borderRadius": "8px",
        "fontSize": "13.5px", "fontWeight": "500",
        "color": "rgba(255,255,255,0.88)", "cursor": "pointer",
        "marginBottom": "2px", "transition": "background 0.15s",
    }
    active_style = {
        **base_style,
        "background": "rgba(255,255,255,0.18)",
        "fontWeight": "700",
        "color": "#ffffff",
        "borderLeft": "3px solid #facc15",
        "paddingLeft": "11px",
    }
    styles = []
    for _, href in NAV_LINKS:
        is_active = (pathname == href) or (pathname is None and href == "/")
        styles.append(active_style if is_active else base_style)
    return styles


# ── AI send button — instant disable on click, browser-side only ──────────────
# Prevents duplicate submissions while a request is in flight without adding
# any server round-trip or touching the actual send/receive logic.
app.clientside_callback(
    """
    function(n_clicks, n_submit) {
        const btn = document.getElementById('ai-send-btn');
        const inp = document.getElementById('ai-input');
        if (btn) { btn.disabled = true; btn.style.opacity = '0.5'; }
        if (inp) { inp.disabled = true; }
        return window.dash_clientside.no_update;
    }
    """,
    Output("ai-send-btn", "title"),
    Input("ai-send-btn", "n_clicks"),
    Input("ai-input",    "n_submit"),
    prevent_initial_call=True,
)

app.clientside_callback(
    """
    function(children) {
        const btn = document.getElementById('ai-send-btn');
        const inp = document.getElementById('ai-input');
        if (btn) { btn.disabled = false; btn.style.opacity = '1'; }
        if (inp) { inp.disabled = false; }
        return window.dash_clientside.no_update;
    }
    """,
    Output("ai-input", "title"),
    Input("ai-messages", "children"),
    prevent_initial_call=True,
)


# ── Mobile sidebar toggle — pure browser-side, touches no Python state ────────
# Clicking the hamburger or the overlay toggles a CSS class on #sidebar.
# This never reaches the server and cannot interfere with any data callback.
app.clientside_callback(
    """
    function(hamburger_clicks, overlay_clicks) {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('mobile-menu-overlay');
        if (!sidebar || !overlay) { return window.dash_clientside.no_update; }
        sidebar.classList.toggle('mobile-open');
        overlay.classList.toggle('mobile-open');
        return window.dash_clientside.no_update;
    }
    """,
    Output("mobile-hamburger-btn", "title"),
    Input("mobile-hamburger-btn", "n_clicks"),
    Input("mobile-menu-overlay",  "n_clicks"),
    prevent_initial_call=True,
)


# ── Auth guard — only active if LOGIN_ENABLED=true ────────────────────────────

@server.before_request
def require_login():
    if not LOGIN_ENABLED:
        return None
    if request.path.startswith(("/login", "/logout", "/_dash", "/assets", "/ping")):
        return None
    if not session.get("logged_in"):
        return redirect("/login")
    return None


@server.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect("/login")


# ── Seed sample data on first load ────────────────────────────────────────────

@app.callback(
    Output("shared-dataset",    "data", allow_duplicate=True),
    Output("app-initialized",   "data"),
    Output("sidebar-data-badge","children"),
    Input("app-initialized",    "data"),
    State("shared-dataset",     "data"),
    prevent_initial_call="initial_duplicate",
)
def initialize(initialized, existing_dataset):
    if initialized:
        badge = _make_badge(existing_dataset)
        return dash.no_update, True, badge

    if existing_dataset and existing_dataset.get("records") and not existing_dataset.get("is_sample"):
        return dash.no_update, True, _make_badge(existing_dataset)

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


# ── AI floating button callbacks ───────────────────────────────────────────────

@app.callback(
    Output("ai-panel",        "style"),
    Output("ai-panel-open",   "data"),
    Output("ai-model-badge",  "children"),
    Input("ai-toggle-btn",    "n_clicks"),
    Input("ai-close-btn",     "n_clicks"),
    State("ai-panel-open",    "data"),
    prevent_initial_call=True,
)
def toggle_ai_panel(open_clicks, close_clicks, is_open):
    triggered = dash.ctx.triggered_id
    new_open  = False if triggered == "ai-close-btn" else not is_open

    base_style = {
        "position": "fixed", "bottom": "90px", "right": "24px", "zIndex": 2000,
        "width": "340px", "background": "#fff", "borderRadius": "12px",
        "boxShadow": "0 8px 32px rgba(0,0,0,0.2)", "border": "1px solid #e5e7eb",
        "display": "block" if new_open else "none",
    }
    model_label = f"· {which_ai()}"
    return base_style, new_open, model_label


@app.callback(
    Output("ai-messages", "children"),
    Output("ai-history",  "data"),
    Output("ai-input",    "value"),
    Input("ai-send-btn",  "n_clicks"),
    Input("ai-input",     "n_submit"),
    State("ai-input",       "value"),
    State("ai-history",     "data"),
    State("shared-dataset",  "data"),
    prevent_initial_call=True,
)
def send_ai_message(n_clicks, n_submit, question, history, shared_dataset):
    if not question or not question.strip():
        return dash.no_update, dash.no_update, dash.no_update

    import pandas as pd
    df = pd.DataFrame(shared_dataset["records"]) if shared_dataset and shared_dataset.get("records") else None

    answer  = ai_ask(question.strip(), df)
    history = (history or []) + [{"q": question.strip(), "a": answer}]

    bubbles = []
    for turn in history[-10:]:
        bubbles.append(html.Div(turn["q"], style={
            "background": "#3e8865", "color": "#fff", "padding": "8px 12px",
            "borderRadius": "12px 12px 2px 12px", "marginBottom": "6px",
            "maxWidth": "85%", "marginLeft": "auto", "fontSize": "12.5px",
        }))
        bubbles.append(html.Div(_render_ai_text(turn["a"]), style={
            "background": "#fff", "color": "#374151", "padding": "8px 12px",
            "borderRadius": "12px 12px 12px 2px", "marginBottom": "12px",
            "maxWidth": "90%", "border": "1px solid #e5e7eb", "fontSize": "12.5px",
            "lineHeight": "1.5",
        }))

    return bubbles, history, ""


def _render_ai_text(text: str):
    """
    Turn plain **bold** markdown and a divider line (---) from the AI or the
    local fallback note into clean Dash elements — no raw asterisks shown.
    """
    lines = text.split("\n")
    children = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            children.append(html.Br())
            continue
        if stripped == "---":
            children.append(html.Hr(style={
                "border": "none", "borderTop": "1px solid #e5e7eb", "margin": "8px 0",
            }))
            continue
        parts = stripped.split("**")
        if len(parts) > 1:
            spans = [html.Strong(p) if i % 2 == 1 else p for i, p in enumerate(parts)]
            children.append(html.Div(spans, style={"marginBottom": "3px"}))
        else:
            children.append(html.Div(stripped, style={"marginBottom": "3px"}))
    return children


@app.callback(
    Output("ai-messages", "children", allow_duplicate=True),
    Output("ai-history",  "data",     allow_duplicate=True),
    Input("ai-clear-btn", "n_clicks"),
    prevent_initial_call=True,
)
def clear_ai_conversation(n_clicks):
    return [], []


@server.route("/ping")
def ping():
    return "pong", 200


if __name__ == "__main__":
    host  = os.getenv("HOST",  "0.0.0.0")
    port  = int(os.getenv("PORT", "10000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    print(f"\n  DericBI running → http://{host}:{port}\n")
    app.run(host=host, port=port, debug=debug)
