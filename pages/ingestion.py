"""
Ingestion page — smart upload with instant column profile on load.
"""
import dash
from dash import html, dcc, dash_table, Input, Output, State, no_update, ctx
import pandas as pd
import numpy as np
import io
import base64
from urllib.parse import quote_plus, urlparse, parse_qs, unquote
# sqlalchemy imported lazily in DB callbacks

dash.register_page(__name__, path="/ingestion", name="Data Ingestion")

layout = html.Div([
    html.H2("Data Ingestion", style={"marginBottom": "4px", "color": "#1f2937"}),
    html.P("Upload a file or connect to a database. Your data is stored in-session only.",
           style={"color": "#6b7280", "marginBottom": "20px", "fontSize": "13px"}),

    # ── Upload card ────────────────────────────────────────────────────────────
    html.Div([
        html.Div([
            html.H4("📁 Upload File", style={"margin": "0 0 12px", "fontSize": "15px", "color": "#374151"}),
            dcc.Upload(
                id="upload-data",
                children=html.Div([
                    html.Div("🗂", style={"fontSize": "32px", "marginBottom": "8px"}),
                    html.Div("Drag & drop or click to select", style={"fontWeight": "600", "color": "#374151"}),
                    html.Div("CSV or Excel (.xlsx / .xls)", style={"fontSize": "12px", "color": "#9ca3af", "marginTop": "4px"}),
                ], style={"textAlign": "center", "padding": "20px 0"}),
                style={
                    "width": "100%", "border": "2px dashed #d1d5db",
                    "borderRadius": "10px", "cursor": "pointer",
                    "background": "#f9fafb", "transition": "border-color 0.2s",
                },
                multiple=False,
            ),
        ], style={
            "background": "#fff", "borderRadius": "10px", "padding": "20px",
            "boxShadow": "0 1px 6px rgba(0,0,0,0.07)", "border": "1px solid #e5e7eb",
            "marginBottom": "16px",
        }),

        # ── Database card ──────────────────────────────────────────────────────
        html.Details([
            html.Summary([
                html.Span("🔌 Connect to Database", style={"fontWeight": "600", "fontSize": "15px", "color": "#374151"}),
            ], style={"cursor": "pointer", "padding": "14px 0", "listStyle": "none"}),
            html.Div([
                html.Div([
                    dcc.Input(
                        id="db-connection-string",
                        type="text",
                        placeholder="Paste full connection string  e.g. postgresql://user:pass@host:5432/db",
                        style={"width": "100%", "marginBottom": "10px", "padding": "8px", "borderRadius": "6px", "border": "1px solid #d1d5db"},
                    ),
                    html.Div(id="connection-parse-message", style={"fontSize": "12px", "color": "#6b7280", "marginBottom": "10px"}),
                ]),
                html.Div([
                    dcc.Dropdown(id="db-type", options=[
                        {"label": "MySQL", "value": "mysql"},
                        {"label": "PostgreSQL / Neon", "value": "postgres"},
                    ], value="mysql", clearable=False,
                    style={"width": "200px", "display": "inline-block", "marginRight": "8px"}),
                    dcc.Input(id="db-host", type="text", placeholder="Host", style={"marginRight": "8px", "padding": "7px", "borderRadius": "6px", "border": "1px solid #d1d5db"}),
                    dcc.Input(id="db-port", type="number", placeholder="Port", value=3306, style={"width": "90px", "marginRight": "8px", "padding": "7px", "borderRadius": "6px", "border": "1px solid #d1d5db"}),
                    dcc.Input(id="db-user", type="text", placeholder="User", style={"marginRight": "8px", "padding": "7px", "borderRadius": "6px", "border": "1px solid #d1d5db"}),
                    dcc.Input(id="db-pass", type="password", placeholder="Password", style={"marginRight": "8px", "padding": "7px", "borderRadius": "6px", "border": "1px solid #d1d5db"}),
                    dcc.Input(id="db-name", type="text", placeholder="Database", style={"marginRight": "8px", "padding": "7px", "borderRadius": "6px", "border": "1px solid #d1d5db"}),
                    dcc.Checklist(id="db-ssl",
                        options=[{"label": " Use SSL", "value": "ssl"}],
                        value=[], style={"display": "inline-block"}),
                ], style={"marginBottom": "10px", "display": "flex", "flexWrap": "wrap", "gap": "4px", "alignItems": "center"}),
                dcc.Textarea(
                    id="db-query",
                    placeholder="SELECT * FROM sales LIMIT 5000",
                    style={"width": "100%", "height": "90px", "borderRadius": "6px", "border": "1px solid #d1d5db", "padding": "8px"},
                ),
                html.Div([
                    html.Button("Test Connection", id="test-db", n_clicks=0, style={
                        "marginRight": "8px", "padding": "7px 16px", "borderRadius": "6px",
                        "border": "1px solid #3e8865", "background": "#fff", "color": "#3e8865",
                        "cursor": "pointer", "fontWeight": "600",
                    }),
                    html.Button("Run Query", id="run-query", n_clicks=0, style={
                        "padding": "7px 16px", "borderRadius": "6px", "border": "none",
                        "background": "#3e8865", "color": "#fff", "cursor": "pointer", "fontWeight": "600",
                    }),
                ], style={"marginTop": "10px"}),
            ], style={"marginTop": "10px"}),
        ], style={
            "background": "#fff", "borderRadius": "10px", "padding": "0 20px 16px",
            "boxShadow": "0 1px 6px rgba(0,0,0,0.07)", "border": "1px solid #e5e7eb",
            "marginBottom": "16px",
        }),
    ]),

    # ── Status message ────────────────────────────────────────────────────────
    html.Div(id="ingestion-message", style={"marginBottom": "14px", "fontSize": "13px"}),

    # ── Column profile (shows on load) ────────────────────────────────────────
    html.Div(id="column-profile"),

    # ── Data preview ──────────────────────────────────────────────────────────
    html.Div(id="preview-table"),
])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _coerce(df):
    out = df.copy()
    for col in out.select_dtypes(include="object").columns:
        converted = pd.to_numeric(out[col], errors="coerce")
        if converted.notna().mean() >= 0.75:
            out[col] = converted
    return out


def _col_type_icon(dtype):
    if pd.api.types.is_numeric_dtype(dtype): return "🔢"
    if pd.api.types.is_datetime64_any_dtype(dtype): return "📅"
    return "🔤"


def _build_column_profile(df):
    """Build an instant column-by-column summary table."""
    df = _coerce(df)
    rows = []
    for col in df.columns:
        s = df[col]
        dtype = s.dtype
        missing = int(s.isna().sum())
        unique  = int(s.nunique(dropna=True))
        completeness = f"{100*(len(s)-missing)/max(len(s),1):.0f}%"
        if pd.api.types.is_numeric_dtype(dtype):
            num = pd.to_numeric(s, errors="coerce").dropna()
            sample = f"min {_fmt(num.min())} / mean {_fmt(num.mean())} / max {_fmt(num.max())}" if not num.empty else "—"
        else:
            top = s.dropna().astype(str).value_counts()
            sample = ", ".join(top.head(3).index.tolist()) if not top.empty else "—"
        rows.append({
            "Column": f"{_col_type_icon(dtype)} {col}",
            "Type": str(dtype),
            "Unique": f"{unique:,}",
            "Missing": f"{missing:,}",
            "Complete": completeness,
            "Sample / Range": sample[:60],
        })
    profile_df = pd.DataFrame(rows)
    return html.Div([
        html.H4("Column Profile", style={"fontSize": "14px", "fontWeight": "700", "color": "#374151", "marginBottom": "10px"}),
        dash_table.DataTable(
            data=profile_df.to_dict("records"),
            columns=[{"name": c, "id": c} for c in profile_df.columns],
            style_table={"overflowX": "auto"},
            style_header={"background": "#f3f4f6", "fontWeight": "700", "fontSize": "12px", "border": "none"},
            style_cell={"fontSize": "12px", "padding": "7px 10px", "border": "1px solid #f3f4f6", "fontFamily": "inherit"},
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#fafafa"},
            ],
            page_size=20,
        ),
    ], style={
        "background": "#fff", "borderRadius": "10px", "padding": "16px 20px",
        "boxShadow": "0 1px 6px rgba(0,0,0,0.07)", "border": "1px solid #e5e7eb",
        "marginBottom": "16px",
    })


def _fmt(v):
    if pd.isna(v): return "N/A"
    if isinstance(v, (float, np.floating)):
        if abs(v) >= 1_000_000: return f"{v/1_000_000:,.1f}M"
        if abs(v) >= 1_000:     return f"{v:,.1f}"
        return f"{v:.2f}"
    return f"{v}"


def _success_msg(text):
    return html.Div(text, style={"background": "rgba(34,197,94,0.1)", "color": "#15803d",
                                  "padding": "10px 14px", "borderRadius": "8px", "border": "1px solid rgba(34,197,94,0.3)"})

def _error_msg(text):
    return html.Div(text, style={"background": "rgba(239,68,68,0.1)", "color": "#dc2626",
                                  "padding": "10px 14px", "borderRadius": "8px", "border": "1px solid rgba(239,68,68,0.3)"})


def parse_contents(contents, filename):
    _, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.StringIO(decoded.decode("utf-8", errors="ignore")))
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(decoded), engine="openpyxl")
        else:
            return None, _error_msg("Unsupported format — upload CSV or Excel."), no_update, no_update
    except Exception as e:
        return None, _error_msg(f"Could not read file: {e}"), no_update, no_update

    profile  = _build_column_profile(df)
    preview  = dash_table.DataTable(
        data=df.head(20).to_dict("records"),
        columns=[{"name": c, "id": c} for c in df.columns],
        style_table={"overflowX": "auto"},
        style_header={"background": "#f3f4f6", "fontWeight": "700", "fontSize": "12px"},
        style_cell={"fontSize": "12px", "padding": "6px 10px"},
        page_size=10,
    )
    dataset  = {"filename": filename, "records": df.to_dict("records")}
    msg      = _success_msg(f"✓ Loaded {filename} — {len(df):,} rows × {len(df.columns)} columns")
    return profile, msg, preview, dataset


def _build_sql_engine(db_type, host, port, user, password, database, use_ssl=False):
    from sqlalchemy import create_engine
    db_type = (db_type or "mysql").strip().lower()
    if db_type == "postgres":
        url = f"postgresql+psycopg2://{quote_plus(user or '')}:{quote_plus(password or '')}@{host}:{int(port)}/{database}{'?sslmode=require' if use_ssl else ''}"
        return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 10})
    url = f"mysql+pymysql://{quote_plus(user or '')}:{quote_plus(password or '')}@{host}:{int(port)}/{database}"
    ca = {"connect_timeout": 10}
    if use_ssl: ca["ssl"] = {}
    return create_engine(url, pool_pre_ping=True, connect_args=ca)


def _build_engine_from_connection_string(connection_string):
    from sqlalchemy import create_engine
    conn = (connection_string or "").strip()
    if conn.startswith("postgresql://"):
        conn = conn.replace("postgresql://", "postgresql+psycopg2://", 1)
    elif conn.startswith("mysql://"):
        conn = conn.replace("mysql://", "mysql+pymysql://", 1)
    return create_engine(conn, pool_pre_ping=True, connect_args={"connect_timeout": 10})


# ── Callbacks ─────────────────────────────────────────────────────────────────

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
            db_type, default_port = "postgres", 5432
        elif "mysql" in scheme:
            db_type, default_port = "mysql", 3306
        else:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, "Scheme not recognised — use postgresql:// or mysql://"
        host     = parsed.hostname
        user     = unquote(parsed.username) if parsed.username else ""
        password = unquote(parsed.password) if parsed.password else ""
        port     = parsed.port or default_port
        db_name  = (parsed.path or "").lstrip("/")
        qp       = parse_qs(parsed.query or "")
        ssl_req  = (qp.get("sslmode", [""])[0] or "").lower() in {"require", "verify-ca", "verify-full"}
        return db_type, host, port, user, password, db_name, (["ssl"] if ssl_req else []), "✓ Connection string parsed — fields filled below"
    except Exception:
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update, "Could not parse — check format"


@dash.callback(
    Output("column-profile", "children"),
    Output("ingestion-message", "children"),
    Output("preview-table", "children"),
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
def update_output(contents, test_clicks, run_clicks, filename,
                  connection_string, db_type, host, port, user, password,
                  database, ssl_values, query):
    trigger = ctx.triggered_id

    if trigger == "upload-data" and contents:
        return parse_contents(contents, filename)

    if trigger in {"test-db", "run-query"}:
        if not connection_string and not all([host, port, user, database]):
            return no_update, _error_msg("Missing DB fields: host, port, user and database are required."), no_update, no_update
        try:
            if connection_string and connection_string.strip():
                engine = _build_engine_from_connection_string(connection_string)
            else:
                engine = _build_sql_engine(db_type, host, port, user, password, database, use_ssl="ssl" in (ssl_values or []))

            if trigger == "test-db":
                with engine.connect() as conn:
                    from sqlalchemy import text
                    conn.execute(text("SELECT 1"))
                return no_update, _success_msg("✓ Database connection successful"), no_update, no_update

            if not query or not query.strip():
                return no_update, _error_msg("Enter a SELECT query first."), no_update, no_update
            if not query.strip().lower().startswith("select"):
                return no_update, _error_msg("Only SELECT queries allowed."), no_update, no_update

            df = pd.read_sql_query(query, engine)
            profile = _build_column_profile(df)
            preview = dash_table.DataTable(
                data=df.head(20).to_dict("records"),
                columns=[{"name": c, "id": c} for c in df.columns],
                style_table={"overflowX": "auto"},
                style_header={"background": "#f3f4f6", "fontWeight": "700", "fontSize": "12px"},
                style_cell={"fontSize": "12px", "padding": "6px 10px"},
                page_size=10,
            )
            dataset = {"filename": f"{db_type}_query", "records": df.to_dict("records")}
            return profile, _success_msg(f"✓ Query returned {len(df):,} rows × {len(df.columns)} columns"), preview, dataset
        except Exception as exc:
            return no_update, _error_msg(f"Database error: {exc}"), no_update, no_update

    return no_update, "", no_update, no_update
