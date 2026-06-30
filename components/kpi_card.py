from dash import html

def kpi_card(title, value, color="#ffdd00"):
    return html.Div(
        [
            html.H3(title, className="kpi-title"),
            html.P(value, className="kpi-value", style={"color": color})
        ],
        className="kpi-card",
        style={
            "flex": "1",
            "minWidth": "200px",
            "background": "rgba(255, 255, 255, 0.05)",
            "borderRadius": "12px",
            "padding": "20px",
            "textAlign": "center",
            "boxShadow": "0 4px 20px rgba(0,0,0,0.3)",
            "transition": "transform 0.2s ease-in-out"
        }
    )
