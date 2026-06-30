from dash import html
import dash_bootstrap_components as dbc
from config.settings import DERICBI_LOGO, DERICBI_SLOGAN

def sidebar():
    return html.Div(
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
                    dbc.NavLink("Home", href="/", active="exact"),
                    dbc.NavLink("Ingestion", href="/ingestion", active="exact"),
                    dbc.NavLink("Cleaning", href="/cleaning", active="exact"),
                    dbc.NavLink("Exploration", href="/exploration", active="exact"),
                    dbc.NavLink("Visualization", href="/visualization", active="exact"),
                    dbc.NavLink("Insights", href="/insights", active="exact"),
                    dbc.NavLink("Reporting", href="/reporting", active="exact"),
                ],
                className="analytics-sidebar-nav",
                vertical=True,
                pills=True,
            ),
        ],
        className="analytics-sidebar",
        style={
            "position": "fixed",
            "top": 0,
            "left": 0,
            "bottom": 0,
            "width": "16rem",
            "padding": "2rem 1rem",
            "backgroundColor": "#3e8865",
            "color": "#ffffff",
            "overflowY": "auto"
        },
    )
