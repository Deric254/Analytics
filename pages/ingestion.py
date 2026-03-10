import dash
from dash import html, dcc, dash_table, Input, Output, State, no_update, ctx
import pandas as pd
import io
import base64
from urllib.parse import quote_plus, urlparse, parse_qs, unquote
from sqlalchemy import create_engine, text

dash.register_page(__name__, path="/ingestion", name="Data Ingestion")

layout = html.Div([
    html.H2("DericBI Analytics Engine - Data Ingestion", className="page-title"),

    html.Div([
        html.H4("How to load data"),
        html.Ol([
            html.Li("Option 1: Upload a CSV or Excel file."),
            html.Li("Option 2: Connect to MySQL or PostgreSQL (Neon), test connection, then run a SELECT query."),
            html.Li("After data is loaded, continue to Cleaning, Exploration, Visualization, Insights, and Reporting."),
        ]),
    ], style={"marginBottom": "15px"}),

    # Upload Section
    html.Div([
        html.Label("Upload CSV/XLSX File"),
        dcc.Upload(
            id="upload-data",
            children=html.Div(["Drag and Drop or Select File"]),
            style={
                "width": "100%", "height": "80px", "lineHeight": "80px",
                "borderWidth": "1px", "borderStyle": "dashed",
                "borderRadius": "5px", "textAlign": "center",
                "margin": "10px"
            },
            multiple=False
        ),
    ]),

    # SQL Connector (collapsible)
    html.Details([
        html.Summary("Connect to Database", style={"cursor": "pointer", "fontWeight": "600"}),
        html.Div([
            dcc.Input(
                id="db-connection-string",
                type="text",
                placeholder="Optional: paste full connection string (recommended for Neon)",
                style={"width": "100%", "marginBottom": "8px"}
            ),
            html.Div(id="connection-parse-message", style={"marginBottom": "8px", "fontSize": "0.9rem"}),
            html.Div([
                dcc.Dropdown(
                    id="db-type",
                    options=[
                        {"label": "MySQL", "value": "mysql"},
                        {"label": "PostgreSQL (Neon)", "value": "postgres"},
                    ],
                    value="mysql",
                    clearable=False,
                    style={"width": "260px", "display": "inline-block", "marginRight": "8px", "marginBottom": "8px"}
                ),
                dcc.Input(id="db-host", type="text", placeholder="Host (e.g. localhost or db.example.com)", style={"marginRight": "8px", "marginBottom": "8px"}),
                dcc.Input(id="db-port", type="number", placeholder="Port", value=3306, style={"width": "110px", "marginRight": "8px", "marginBottom": "8px"}),
                dcc.Input(id="db-user", type="text", placeholder="User", style={"marginRight": "8px", "marginBottom": "8px"}),
                dcc.Input(id="db-pass", type="password", placeholder="Password", style={"marginRight": "8px", "marginBottom": "8px"}),
                dcc.Input(id="db-name", type="text", placeholder="Database", style={"marginRight": "8px", "marginBottom": "8px"}),
                dcc.Checklist(
                    id="db-ssl",
                    options=[{"label": " Use SSL (recommended for online DB)", "value": "ssl"}],
                    value=[],
                    style={"display": "inline-block", "marginBottom": "8px"}
                ),
            ]),
            dcc.Textarea(
                id="db-query",
                placeholder="Write SELECT query here, e.g. SELECT * FROM sales LIMIT 1000",
                style={"width": "100%", "height": "120px", "marginTop": "8px"},
            ),
            html.Div([
                html.Button("Test Connection", id="test-db", n_clicks=0, style={"marginRight": "8px"}),
                html.Button("Run Query", id="run-query", n_clicks=0),
            ], style={"marginTop": "10px"}),
            html.Div(
                "MySQL default port: 3306. PostgreSQL/Neon default port: 5432. For Neon, use PostgreSQL + enable SSL.",
                style={"marginTop": "8px", "fontSize": "0.9rem"}
            )
        ], style={"marginTop": "10px"})
    ], style={"marginTop": "20px"}),

    # Preview Table
    html.Div(id="preview-table", style={"marginTop": "20px"}),

    # Validation/Error Messages
    html.Div(id="ingestion-message", style={"marginTop": "10px", "color": "red"})
])

# Callbacks
def parse_contents(contents, filename):
    _, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8', errors='ignore')))
        elif filename.endswith(('.xlsx', '.xls')):
            try:
                df = pd.read_excel(io.BytesIO(decoded), engine="openpyxl")
            except ImportError:
                return None, "Excel support requires openpyxl. Install with: pip install openpyxl", no_update
        else:
            return None, "Unsupported file format. Please upload CSV or Excel.", no_update

        table = dash_table.DataTable(
            data=df.head(10).to_dict("records"),
            columns=[{"name": i, "id": i} for i in df.columns],
            style_table={"overflowX": "auto"}
        )
        dataset = {
            "filename": filename,
            "records": df.to_dict("records")
        }
        return table, f"Loaded {filename} with {len(df)} rows and {len(df.columns)} columns.", dataset
    except Exception as e:
        return None, f"Error processing file: {str(e)}", no_update


def _build_sql_engine(db_type, host, port, user, password, database, use_ssl=False):
    db_type = (db_type or "mysql").strip().lower()

    if db_type == "postgres":
        normalized_host = (host or "").replace("postgresql://", "").replace("postgresql+psycopg2://", "").strip()
        encoded_user = quote_plus((user or "").strip())
        encoded_password = quote_plus(password or "")
        ssl_suffix = "?sslmode=require" if use_ssl else ""
        connection_url = f"postgresql+psycopg2://{encoded_user}:{encoded_password}@{normalized_host}:{int(port)}/{database.strip()}{ssl_suffix}"
        connect_args = {"connect_timeout": 10}
        if use_ssl:
            connect_args["sslmode"] = "require"
            connect_args["channel_binding"] = "require"
        return create_engine(connection_url, pool_pre_ping=True, connect_args=connect_args)

    normalized_host = (host or "").replace("mysql://", "").replace("mysql+pymysql://", "").strip()
    encoded_user = quote_plus((user or "").strip())
    encoded_password = quote_plus(password or "")
    connection_url = f"mysql+pymysql://{encoded_user}:{encoded_password}@{normalized_host}:{int(port)}/{database.strip()}"

    connect_args = {"connect_timeout": 10}
    if use_ssl:
        connect_args["ssl"] = {}
    return create_engine(connection_url, pool_pre_ping=True, connect_args=connect_args)


def _build_engine_from_connection_string(connection_string):
    conn_str = (connection_string or "").strip()
    if not conn_str:
        return None

    normalized = conn_str
    connect_args = {"connect_timeout": 10}

    if conn_str.startswith("postgresql://"):
        normalized = conn_str.replace("postgresql://", "postgresql+psycopg2://", 1)
    elif conn_str.startswith("mysql://"):
        normalized = conn_str.replace("mysql://", "mysql+pymysql://", 1)

    return create_engine(normalized, pool_pre_ping=True, connect_args=connect_args)


@dash.callback(
    Output("db-type", "value"),
    Output("db-host", "value"),
    Output("db-port", "value"),
    Output("db-user", "value"),
    Output("db-pass", "value"),
    Output("db-name", "value"),
    Output("db-ssl", "value"),
    Output("connection-parse-message", "children"),
    Input("db-connection-string", "value"),
    prevent_initial_call=True,
)
def parse_connection_string(connection_string):
    conn_str = (connection_string or "").strip()
    if not conn_str:
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update, ""

    try:
        parsed = urlparse(conn_str)
        scheme = (parsed.scheme or "").lower()

        if "postgres" in scheme:
            db_type = "postgres"
            default_port = 5432
        elif "mysql" in scheme:
            db_type = "mysql"
            default_port = 3306
        else:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, "Connection string scheme not recognized. Use postgresql:// or mysql://"

        host = parsed.hostname
        user = unquote(parsed.username) if parsed.username else ""
        password = unquote(parsed.password) if parsed.password else ""
        port = parsed.port or default_port
        db_name = (parsed.path or "").lstrip("/")

        query_params = parse_qs(parsed.query or "")
        ssl_required = False
        sslmode = (query_params.get("sslmode", [""])[0] or "").lower()
        if sslmode in {"require", "verify-ca", "verify-full"}:
            ssl_required = True

        ssl_values = ["ssl"] if ssl_required else []

        if not all([host, user, db_name]):
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, "Could not extract all fields. Ensure format: protocol://user:pass@host:port/dbname"

        return db_type, host, port, user, password, db_name, ssl_values, "Connection string parsed. You can now click Test Connection."
    except Exception:
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update, "Could not parse connection string. Check format and try again."

@dash.callback(
    Output("preview-table", "children"),
    Output("ingestion-message", "children"),
    Output("shared-dataset", "data"),
    Input("upload-data", "contents"),
    Input("test-db", "n_clicks"),
    Input("run-query", "n_clicks"),
    State("upload-data", "filename"),
    State("db-connection-string", "value"),
    State("db-type", "value"),
    State("db-host", "value"),
    State("db-port", "value"),
    State("db-user", "value"),
    State("db-pass", "value"),
    State("db-name", "value"),
    State("db-ssl", "value"),
    State("db-query", "value"),
    prevent_initial_call=True,
)
def update_output(contents, test_clicks, run_clicks, filename, connection_string, db_type, host, port, user, password, database, ssl_values, query):
    trigger = ctx.triggered_id

    if trigger == "upload-data" and contents is not None:
        table, message, dataset = parse_contents(contents, filename)
        return table, message, dataset

    if trigger in {"test-db", "run-query"}:
        if not connection_string and not all([host, port, user, database]):
            return no_update, "Missing DB details: host, port, user and database are required.", no_update

        try:
            if connection_string and connection_string.strip():
                engine = _build_engine_from_connection_string(connection_string)
                source_label = "connection string"
            else:
                use_ssl = "ssl" in (ssl_values or [])
                engine = _build_sql_engine(db_type, host, port, user, password, database, use_ssl=use_ssl)
                source_label = db_type or "database"

            if trigger == "test-db":
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                return no_update, f"Database connection successful ({source_label}).", no_update

            if not query or not query.strip():
                return no_update, "Please provide a SQL query (SELECT ...).", no_update

            stripped_query = query.strip().lower()
            if not stripped_query.startswith("select"):
                return no_update, "Only SELECT queries are allowed in ingestion for safety.", no_update

            df = pd.read_sql_query(query, engine)
            table = dash_table.DataTable(
                data=df.head(50).to_dict("records"),
                columns=[{"name": i, "id": i} for i in df.columns],
                page_size=10,
                style_table={"overflowX": "auto"}
            )
            dataset = {
                "filename": f"{(db_type or 'db')}_query_{(database or 'dataset')}",
                "records": df.to_dict("records")
            }
            return table, f"Query loaded successfully: {len(df)} rows, {len(df.columns)} columns.", dataset

        except Exception as exc:
            return no_update, f"Database error: {str(exc)}", no_update

    return no_update, "", no_update
