"""
Login page — simple password gate. No database, no user table.
Password is set via LOGIN_PASSWORD environment variable (defaults to 'dericbi' for local testing).
"""
import dash
from dash import html, dcc, Input, Output, State
from flask import session

dash.register_page(__name__, path="/login", name="Login")

BRAND = "#3e8865"

layout = html.Div([
    html.Div([
        html.Div("DericBI", style={
            "fontSize": "32px", "fontWeight": "800", "color": BRAND,
            "textAlign": "center", "marginBottom": "4px",
        }),
        html.Div("Analytics Engine", style={
            "fontSize": "13px", "color": "#9ca3af", "textAlign": "center", "marginBottom": "30px",
        }),

        dcc.Input(
            id="login-password", type="password", placeholder="Enter password",
            n_submit=0,
            style={
                "width": "100%", "padding": "12px 14px", "borderRadius": "8px",
                "border": "1px solid #d1d5db", "fontSize": "14px", "marginBottom": "12px",
                "boxSizing": "border-box",
            },
        ),

        html.Button("Log In", id="login-btn", n_clicks=0, style={
            "width": "100%", "padding": "12px", "borderRadius": "8px", "border": "none",
            "background": BRAND, "color": "#fff", "fontWeight": "700", "fontSize": "14px",
            "cursor": "pointer",
        }),

        html.Div(id="login-message", style={"marginTop": "14px", "fontSize": "13px", "textAlign": "center"}),
    ], style={
        "background": "#fff", "borderRadius": "14px", "padding": "40px 36px",
        "boxShadow": "0 4px 24px rgba(0,0,0,0.08)", "width": "340px",
    }),
], style={
    "display": "flex", "alignItems": "center", "justifyContent": "center",
    "minHeight": "100vh", "background": "#f0fdf4",
})


@dash.callback(
    Output("login-message", "children"),
    Output("url", "pathname"),
    Output("auth-state", "data"),
    Input("login-btn", "n_clicks"),
    Input("login-password", "n_submit"),
    State("login-password", "value"),
    prevent_initial_call=True,
)
def check_login(n_clicks, n_submit, password):
    import os
    correct = os.getenv("LOGIN_PASSWORD", "dericbi")

    if not password:
        return html.Span("Enter a password.", style={"color": "#dc2626"}), dash.no_update, dash.no_update

    if password == correct:
        session["logged_in"] = True
        return html.Span("✓ Logged in", style={"color": "#15803d"}), "/", True

    return html.Span("Incorrect password.", style={"color": "#dc2626"}), dash.no_update, dash.no_update
