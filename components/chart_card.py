from dash import html, dcc

def chart_card(title, figure):
    return html.Div(
        [
            html.H4(title, className="chart-title"),
            dcc.Graph(figure=figure, style={"height": "400px"})
        ],
        className="chart-card",
        style={
            "background": "rgba(255, 255, 255, 0.05)",
            "borderRadius": "12px",
            "padding": "20px",
            "marginBottom": "20px",
            "boxShadow": "0 4px 20px rgba(0,0,0,0.3)"
        }
    )
