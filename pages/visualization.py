"""
Visualization — 7 auto-generated business charts using DataProfile.
All charts have clean data labels. Custom builder supports saving multiple charts.
Saved charts can be exported to PDF with auto-generated explanations.
"""
import io
import base64
import dash
from dash import html, dcc, Input, Output, State, ctx, ALL, MATCH
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import numpy as np
from services.insights_agent import DataProfile, _coerce, _series, _fmt, _pct, _chg

dash.register_page(__name__, path="/visualization", name="Visualization")

BRAND = "#3e8865"
CFG   = {"displaylogo":False,"responsive":True,
          "toImageButtonOptions":{"format":"png","filename":"dericbi_chart","scale":2}}

def _card(title, children):
    return html.Div([
        html.Div(title, style={"fontSize":"13px","fontWeight":"700","color":"#374151",
                               "borderBottom":"2px solid #e5e7eb","paddingBottom":"6px",
                               "marginBottom":"12px"}),
        *children,
    ], style={"background":"#fff","borderRadius":"10px","padding":"16px 18px",
               "boxShadow":"0 1px 6px rgba(0,0,0,0.07)","border":"1px solid #e5e7eb",
               "marginBottom":"16px"})

def _kpi(title, value, sub="", color=BRAND):
    return html.Div([
        html.Div(title,  style={"fontSize":"11px","fontWeight":"600","color":"#6b7280","textTransform":"uppercase"}),
        html.Div(value,  style={"fontSize":"24px","fontWeight":"700","color":color,"margin":"4px 0"}),
        html.Div(sub,    style={"fontSize":"11px","color":"#9ca3af"}),
    ], style={"background":"#fff","borderRadius":"10px","padding":"14px 16px","flex":"1","minWidth":"130px",
               "boxShadow":"0 1px 6px rgba(0,0,0,0.07)","border":"1px solid #e5e7eb"})


layout = html.Div([
    html.H2("Visualization", style={"marginBottom":"4px","color":"#1f2937"}),
    html.P("Charts auto-generate from your data. Use the builder below for custom views.",
           style={"color":"#6b7280","fontSize":"13px","marginBottom":"20px"}),

    # KPI strip
    dcc.Loading(
        html.Div(id="viz-kpis",
                 style={"display":"flex","gap":"14px","flexWrap":"wrap","marginBottom":"20px"}),
        type="dot"),

    # Auto charts
    dcc.Loading(html.Div(id="viz-auto"), type="circle"),

    # Custom builder
    html.Details([
        html.Summary(html.Span("🛠  Custom Chart Builder",
            style={"fontWeight":"700","fontSize":"14px","color":"#374151","cursor":"pointer"}),
            style={"padding":"14px 0","listStyle":"none","userSelect":"none"}),

        html.Div([
            # Controls row
            html.Div([
                html.Div([
                    html.Label("Chart type", style={"fontSize":"12px","fontWeight":"600","color":"#6b7280"}),
                    dcc.Dropdown(id="viz-type", value="bar", clearable=False, options=[
                        {"label":"Bar",        "value":"bar"},
                        {"label":"Line",       "value":"line"},
                        {"label":"Area",       "value":"area"},
                        {"label":"Scatter",    "value":"scatter"},
                        {"label":"Pie",        "value":"pie"},
                        {"label":"Donut",      "value":"donut"},
                        {"label":"Pareto",     "value":"pareto"},
                        {"label":"Box",        "value":"box"},
                        {"label":"Violin",     "value":"violin"},
                        {"label":"Histogram",  "value":"histogram"},
                        {"label":"Heatmap",    "value":"heatmap"},
                        {"label":"Funnel",     "value":"funnel"},
                        {"label":"Waterfall",  "value":"waterfall"},
                        {"label":"Bubble",     "value":"bubble"},
                    ]),
                ], style={"flex":"1","minWidth":"120px"}),
                html.Div([
                    html.Label("X axis", style={"fontSize":"12px","fontWeight":"600","color":"#6b7280"}),
                    dcc.Dropdown(id="viz-x", placeholder="X column"),
                ], style={"flex":"1","minWidth":"120px"}),
                html.Div([
                    html.Label("Y axis", style={"fontSize":"12px","fontWeight":"600","color":"#6b7280"}),
                    dcc.Dropdown(id="viz-y", placeholder="Y column(s)", multi=True),
                ], style={"flex":"1","minWidth":"120px"}),
                html.Div([
                    html.Label("Color / Group", style={"fontSize":"12px","fontWeight":"600","color":"#6b7280"}),
                    dcc.Dropdown(id="viz-color", placeholder="None"),
                ], style={"flex":"1","minWidth":"120px"}),
                html.Div([
                    html.Label("Aggregation", style={"fontSize":"12px","fontWeight":"600","color":"#6b7280"}),
                    dcc.Dropdown(id="viz-agg", value="sum", clearable=False, options=[
                        {"label":"Sum",   "value":"sum"},
                        {"label":"Mean",  "value":"mean"},
                        {"label":"Count", "value":"count"},
                        {"label":"Max",   "value":"max"},
                        {"label":"Min",   "value":"min"},
                    ]),
                ], style={"flex":"1","minWidth":"100px"}),
            ], style={"display":"flex","flexWrap":"wrap","gap":"10px","marginBottom":"12px"}),

            # Filter row
            html.Div([
                html.Div([
                    html.Label("Filter column", style={"fontSize":"12px","fontWeight":"600","color":"#6b7280"}),
                    dcc.Dropdown(id="viz-fcol", placeholder="Optional"),
                ], style={"flex":"1"}),
                html.Div([
                    html.Label("Filter values", style={"fontSize":"12px","fontWeight":"600","color":"#6b7280"}),
                    dcc.Dropdown(id="viz-fval", multi=True, placeholder="All values"),
                ], style={"flex":"2"}),
            ], style={"display":"flex","gap":"10px","marginBottom":"14px"}),

            # Chart title override
            html.Div([
                html.Label("Chart title (optional)", style={"fontSize":"12px","fontWeight":"600","color":"#6b7280"}),
                dcc.Input(id="viz-title-override", type="text", placeholder="Leave blank for auto title",
                          style={"width":"100%","padding":"6px 10px","borderRadius":"6px",
                                 "border":"1px solid #d1d5db","fontSize":"13px"}),
            ], style={"marginBottom":"14px"}),

            html.Div([
                html.Button("🔍 Preview Chart", id="viz-build", n_clicks=0, style={
                    "padding":"8px 18px","background":BRAND,"color":"#fff","border":"none",
                    "borderRadius":"6px","cursor":"pointer","fontWeight":"700","fontSize":"13px",
                    "marginRight":"10px",
                }),
                html.Button("💾 Save to Gallery", id="viz-save", n_clicks=0, style={
                    "padding":"8px 18px","background":"#fff","color":BRAND,
                    "border":f"1px solid {BRAND}","borderRadius":"6px",
                    "cursor":"pointer","fontWeight":"700","fontSize":"13px",
                    "marginRight":"10px",
                }),
                html.Button("📄 Export Gallery to PDF", id="viz-export-pdf", n_clicks=0, style={
                    "padding":"8px 18px","background":"#1f2937","color":"#fff","border":"none",
                    "borderRadius":"6px","cursor":"pointer","fontWeight":"700","fontSize":"13px",
                }),
                dcc.Download(id="viz-pdf-download"),
            ], style={"marginBottom":"12px"}),

            # Status message
            html.Div(id="viz-save-msg", style={"fontSize":"12px","color":BRAND,"marginBottom":"8px","minHeight":"18px"}),

            # Preview
            dcc.Loading(
                dcc.Graph(id="viz-custom",
                          figure={"data":[],"layout":{"title":"Configure and click Preview Chart"}},
                          config=CFG, style={"marginTop":"4px"}),
                type="dot"),

        ], style={"padding":"0 0 16px"}),
    ], id="viz-builder-details",
       style={"background":"#fff","borderRadius":"10px","padding":"0 18px",
               "boxShadow":"0 1px 6px rgba(0,0,0,0.07)","border":"1px solid #e5e7eb",
               "marginTop":"16px"}),

    # Saved charts gallery
    html.Div(id="viz-gallery-section", style={"marginTop":"20px"}),

    # Store for saved charts (list of dicts with title + figure JSON)
    dcc.Store(id="viz-saved-charts", storage_type="session", data=[]),
    # Store current preview figure JSON for save
    dcc.Store(id="viz-preview-store", storage_type="session"),
    # Static hidden clear button — must exist in layout for Dash to register Input()
    html.Button(id="viz-clear-gallery", n_clicks=0, style={"display":"none"}),
])


# ── Auto charts ───────────────────────────────────────────────────────────────

def _apply_data_labels_bar(fig, threshold_pct=0.02):
    """Apply clean outside data labels to bar traces."""
    fig.update_traces(
        selector=dict(type="bar"),
        texttemplate="%{value:,.0f}",
        textposition="outside",
        textfont=dict(size=10, color="#374151"),
    )
    return fig

def _apply_data_labels_line(fig):
    fig.update_traces(
        selector=dict(type="scatter", mode="lines+markers"),
        texttemplate="%{y:,.0f}",
        textposition="top center",
        textfont=dict(size=9, color="#374151"),
        mode="lines+markers+text",
    )
    return fig


@dash.callback(
    Output("viz-kpis", "children"),
    Output("viz-auto", "children"),
    Input("shared-dataset", "data"),
)
def auto_charts(shared_dataset):
    if not shared_dataset or not shared_dataset.get("records"):
        return [], html.Div("Upload data on the Ingestion page to auto-generate charts.",
                            style={"color":"#9ca3af","padding":"40px","textAlign":"center"})

    df   = _coerce(pd.DataFrame(shared_dataset["records"]))
    p    = DataProfile(df)
    num  = p.value_col
    cat  = p.group_cols[0] if p.group_cols else None
    cat2 = p.group_cols[1] if len(p.group_cols) > 1 else None
    dc   = p.date_col

    # KPI strip
    missing    = int(df.isna().sum().sum())
    total_c    = p.rows * p.cols_count
    kpis = [_kpi("Records", f"{p.rows:,}", f"{p.cols_count} cols")]
    kpis.append(_kpi("Complete", f"{_pct(total_c-missing,total_c)}",
                     "no gaps" if not missing else f"{missing:,} gaps",
                     color="#22c55e" if not missing else "#f59e0b"))
    if num:
        s = _series(df, num)
        kpis.append(_kpi(f"Total {num}", _fmt(s.sum()), f"avg {_fmt(s.mean())}"))
        kpis.append(_kpi(f"Peak {num}",  _fmt(s.max()), f"low {_fmt(s.min())}"))

    charts = []

    # 1. Trend over time
    if dc and num:
        tmp = df.copy()
        tmp[dc] = pd.to_datetime(tmp[dc], errors="coerce")
        tmp[num] = pd.to_numeric(tmp[num], errors="coerce")
        tmp = tmp.dropna(subset=[dc,num]).sort_values(dc)
        days = (tmp[dc].max()-tmp[dc].min()).days
        code = "Q" if days>365 else "M" if days>60 else "W"
        tmp["_p"] = tmp[dc].dt.to_period(code).astype(str)
        agg = tmp.groupby("_p")[num].sum().reset_index()
        agg.columns = ["Period", num]
        chg = _chg(agg[num].iloc[-1], agg[num].iloc[0]) if len(agg)>=2 else ""
        agg = agg.dropna(subset=[num])
        fig = px.area(agg, x="Period", y=num, title=f"{num} over time  {chg}",
                      color_discrete_sequence=[BRAND], text=num)
        fig.update_traces(line_width=2.5, connectgaps=False,
                          texttemplate="%{text:,.0f}", textposition="top center",
                          textfont=dict(size=9, color="#374151"))
        fig.update_layout(template="plotly_white",margin=dict(t=50,l=40,r=20,b=50),height=300)
        charts.append(_card(f"📈 {num} Trend",[dcc.Graph(figure=fig,config=CFG)]))

    # 2. Top performers
    if cat and num:
        agg = df.groupby(cat,dropna=False)[num].sum().sort_values(ascending=False).head(12).reset_index()
        grand = agg[num].sum()
        agg["label"] = agg[num].apply(_fmt) + " (" + (agg[num]/grand*100).round(1).astype(str) + "%)"
        fig = px.bar(agg, x=num, y=cat, orientation="h",
                     title=f"Top {cat} by {num}",
                     text="label", color=num,
                     color_continuous_scale=["#d1fae5",BRAND])
        fig.update_traces(textposition="outside", textfont=dict(size=10, color="#374151"))
        fig.update_layout(template="plotly_white",margin=dict(t=50,l=10,r=80,b=40),
                          height=320,yaxis={"categoryorder":"total ascending"},
                          coloraxis_showscale=False)
        charts.append(_card(f"🏆 Top Performers — {cat}",[dcc.Graph(figure=fig,config=CFG)]))

    # 3. Pareto 80/20
    if cat and num:
        agg = df.groupby(cat,dropna=False)[num].sum().sort_values(ascending=False).reset_index()
        agg.columns = [cat, num]
        total = agg[num].sum()
        agg["cum%"] = agg[num].cumsum()/total*100 if total else 0
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=agg[cat], y=agg[num], name=num, marker_color=BRAND,
            text=[_fmt(v) for v in agg[num]],
            textposition="outside",
            textfont=dict(size=9, color="#374151"),
        ))
        fig.add_trace(go.Scatter(x=agg[cat], y=agg["cum%"], name="Cumulative %",
                                 yaxis="y2", mode="lines+markers+text",
                                 text=[f"{v:.0f}%" for v in agg["cum%"]],
                                 textposition="top center",
                                 textfont=dict(size=9, color="#f59e0b"),
                                 line=dict(color="#f59e0b",width=2.5)))
        fig.add_hline(y=80, line_dash="dot", line_color="#ef4444",
                      annotation_text="80%", yref="y2")
        fig.update_layout(
            title=f"Pareto 80/20 — {num} by {cat}",
            yaxis=dict(title=num),
            yaxis2=dict(title="Cumulative %",overlaying="y",side="right",range=[0,118]),
            template="plotly_white",height=320,
            margin=dict(t=50,l=40,r=60,b=60),
            legend=dict(orientation="h",y=-0.2),
        )
        charts.append(_card("📊 80/20 Pareto — Where is value concentrated?",[dcc.Graph(figure=fig,config=CFG)]))

    # 4. Cross-category comparison
    if cat and cat2 and num:
        pivot = df.groupby([cat,cat2],dropna=False)[num].sum().reset_index()
        fig = px.bar(pivot, x=cat, y=num, color=cat2, barmode="group",
                     title=f"{num} — {cat} vs {cat2}",
                     color_discrete_sequence=px.colors.qualitative.Safe,
                     text_auto=True)
        fig.update_traces(texttemplate="%{value:,.0f}", textposition="outside",
                          textfont=dict(size=9, color="#374151"))
        fig.update_layout(template="plotly_white",height=320,
                          margin=dict(t=50,l=40,r=20,b=60))
        charts.append(_card(f"⚖️ Comparison: {cat} × {cat2}",[dcc.Graph(figure=fig,config=CFG)]))
    elif cat and num:
        agg = df.groupby(cat,dropna=False)[num].sum().reset_index()
        fig = px.pie(agg, names=cat, values=num, title=f"Share of {num} by {cat}",
                     color_discrete_sequence=px.colors.qualitative.Safe)
        fig.update_traces(
            textinfo="label+percent+value",
            texttemplate="<b>%{label}</b><br>%{percent:.1%}<br>%{value:,.0f}",
            textposition="outside",
            textfont=dict(size=10),
            pull=[0.03]*len(agg),
        )
        fig.update_layout(margin=dict(t=50,l=0,r=0,b=60),height=340,
                          showlegend=True,legend=dict(orientation="h",y=-0.15))
        charts.append(_card(f"🥧 {cat} Market Share",[dcc.Graph(figure=fig,config=CFG)]))

    # 5. Revenue vs Cost vs Margin
    nums_all = p.numeric_cols
    rev_kw   = ["revenue","sales","income","amount","total","value","gross","receipts"]
    cost_kw  = ["cost","expense","cogs","overhead","spend","outgoing"]
    rev_col  = next((c for kw in rev_kw  for c in nums_all if kw in c.lower()), None)
    cost_col = next((c for kw in cost_kw for c in nums_all if kw in c.lower() and c != rev_col), None)

    if rev_col and cost_col and cat:
        agg = df.groupby(cat,dropna=False).agg(
            Revenue=(rev_col,"sum"), Cost=(cost_col,"sum")
        ).reset_index()
        agg["Profit"] = agg["Revenue"]-agg["Cost"]
        agg["Margin%"] = (agg["Profit"]/agg["Revenue"].replace(0,np.nan)*100).round(1)
        agg = agg.sort_values("Profit",ascending=False)
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Revenue",x=agg[cat],y=agg["Revenue"],marker_color=BRAND,
                             text=[_fmt(v) for v in agg["Revenue"]],
                             textposition="outside",textfont=dict(size=9,color=BRAND)))
        fig.add_trace(go.Bar(name="Cost",   x=agg[cat],y=agg["Cost"],marker_color="#f87171",
                             text=[_fmt(v) for v in agg["Cost"]],
                             textposition="outside",textfont=dict(size=9,color="#dc2626")))
        fig.add_trace(go.Scatter(name="Margin %",x=agg[cat],y=agg["Margin%"],
                                 mode="lines+markers+text",yaxis="y2",
                                 text=agg["Margin%"].apply(lambda v: f"{v:.1f}%" if pd.notna(v) else ""),
                                 textposition="top center",
                                 textfont=dict(size=10,color="#b45309"),
                                 line=dict(color="#f59e0b",width=2.5)))
        fig.update_layout(
            barmode="group",
            title=f"Revenue vs Cost vs Margin by {cat}",
            yaxis=dict(title="Amount"),
            yaxis2=dict(title="Margin %",overlaying="y",side="right"),
            template="plotly_white",height=340,
            margin=dict(t=50,l=40,r=60,b=60),
            legend=dict(orientation="h",y=-0.2),
        )
        charts.append(_card("💰 Profitability: Revenue vs Cost vs Margin",[dcc.Graph(figure=fig,config=CFG)]))

    # 6. Correlation heatmap
    good_nums = [c for c in p.numeric_cols
                 if not (_series(df,c).is_monotonic_increasing and _series(df,c).nunique()==p.rows)]
    if len(good_nums) >= 3:
        corr = df[good_nums[:8]].corr(numeric_only=True).round(2)
        fig  = px.imshow(corr, text_auto=True, color_continuous_scale="RdYlGn",
                         zmin=-1, zmax=1,
                         title="Correlation Matrix — which numbers move together?")
        fig.update_traces(texttemplate="%{z:.2f}", textfont=dict(size=10))
        fig.update_layout(template="plotly_white",height=380,
                          margin=dict(t=50,l=10,r=10,b=10))
        charts.append(_card("🔗 Correlation Heatmap",[dcc.Graph(figure=fig,config=CFG)]))

    # 7. Period-over-period growth rate
    if dc and num:
        tmp = df.copy()
        tmp[dc] = pd.to_datetime(tmp[dc],errors="coerce")
        tmp[num] = pd.to_numeric(tmp[num],errors="coerce")
        tmp = tmp.dropna(subset=[dc,num]).sort_values(dc)
        days = (tmp[dc].max()-tmp[dc].min()).days
        code = "M" if days>60 else "W"
        tmp["_p"] = tmp[dc].dt.to_period(code).astype(str)
        agg = tmp.groupby("_p")[num].sum().reset_index()
        agg.columns = ["Period",num]
        if len(agg) >= 3:
            agg["Growth%"] = agg[num].pct_change()*100
            agg = agg.dropna(subset=["Growth%"])
            agg["clr"] = agg["Growth%"].apply(lambda x: "#22c55e" if x>=0 else "#ef4444")
            fig = go.Figure(go.Bar(
                x=agg["Period"],y=agg["Growth%"],
                marker_color=agg["clr"],
                text=[f"{v:+.1f}%" for v in agg["Growth%"]],
                textposition="outside",
                textfont=dict(size=9,color="#374151"),
            ))
            fig.add_hline(y=0,line_color="#9ca3af",line_width=1)
            fig.update_layout(title=f"Period-over-Period Growth — {num} % change",
                              template="plotly_white",height=300,
                              margin=dict(t=50,l=40,r=20,b=60))
            charts.append(_card("📉📈 Growth Rate",[dcc.Graph(figure=fig,config=CFG)]))

    if not charts:
        return kpis, html.Div(
            "Upload data with at least one numeric column to generate charts.",
            style={"color":"#9ca3af","padding":"30px","textAlign":"center"})

    return kpis, html.Div(charts)


# ── Custom builder — dropdowns ────────────────────────────────────────────────

@dash.callback(
    Output("viz-x",    "options"),
    Output("viz-y",    "options"),
    Output("viz-color","options"),
    Output("viz-fcol", "options"),
    Input("shared-dataset","data"),
)
def populate_builder(shared_dataset):
    if not shared_dataset or not shared_dataset.get("records"):
        return [], [], [], []
    df = _coerce(pd.DataFrame(shared_dataset["records"]))
    opts = [{"label":c,"value":c} for c in df.columns]
    return opts, opts, [{"label":"None","value":""}]+opts, opts


@dash.callback(
    Output("viz-fval","options"),
    Input("shared-dataset","data"),
    Input("viz-fcol",      "value"),
)
def fval_opts(shared_dataset, col):
    if not shared_dataset or not col: return []
    df = pd.DataFrame(shared_dataset["records"])
    if col not in df.columns: return []
    vals = sorted(df[col].dropna().astype(str).unique())[:200]
    return [{"label":v,"value":v} for v in vals]


# ── Build helper (shared between preview and save) ────────────────────────────

def _build_figure(shared_dataset, chart_type, x, y, color, agg, fcol, fval, title_override):
    if not shared_dataset or not shared_dataset.get("records"):
        return None, "No data loaded"

    df = _coerce(pd.DataFrame(shared_dataset["records"]))
    p  = DataProfile(df)

    if fcol and fcol in df.columns and fval:
        df = df[df[fcol].astype(str).isin(fval)]
    if df.empty:
        return None, "No rows after filter"

    y_list = [y] if isinstance(y, str) else (y or [])
    y_list = [c for c in y_list if c and c in df.columns]
    if not y_list:
        y_list = [p.value_col] if p.value_col else (p.numeric_cols[:1] if p.numeric_cols else [])
    if not y_list:
        return None, "Select at least one Y column"

    y_col  = y_list[0]
    x      = x or (p.group_cols[0] if p.group_cols else df.columns[0])
    color_use = color if color and color in df.columns else None

    # Aggregate for bar/line/area
    if chart_type in ("bar","line","area","pareto","funnel","waterfall") and x and x in df.columns and y_col in df.columns:
        num_check = pd.to_numeric(df[y_col], errors="coerce")
        if num_check.notna().mean() >= 0.5:
            agg_map = {"sum":"sum","mean":"mean","count":"size","max":"max","min":"min"}
            fn = agg_map.get(agg,"sum")
            if fn == "size":
                df_agg = df.groupby(x,dropna=False).size().reset_index(name="Count")
                y_col = "Count"
                y_list = ["Count"]
            else:
                if len(y_list) > 1:
                    df_agg = df.groupby(x,dropna=False)[y_list].agg(fn).reset_index()
                else:
                    df_agg = df.groupby(x,dropna=False)[y_col].agg(fn).reset_index()
            df = df_agg

    # Sort for line/area
    if chart_type in ("line","area") and x and x in df.columns:
        try:
            df = df.copy()
            df["__sort__"] = pd.to_datetime(df[x], errors="coerce")
            if df["__sort__"].notna().mean() >= 0.6:
                df = df.sort_values("__sort__").drop(columns=["__sort__"])
            else:
                df["__sort__"] = pd.to_numeric(df[x], errors="coerce")
                df = df.sort_values("__sort__").drop(columns=["__sort__"])
        except Exception:
            df = df.sort_values(x)
        drop_cols = [c for c in y_list if c in df.columns]
        if drop_cols:
            df = df.dropna(subset=drop_cols)

    auto_title = f"{y_col} by {x}" if x else y_col

    try:
        if chart_type == "bar":
            if len(y_list) > 1:
                fig = px.bar(df.head(40), x=x, y=y_list, barmode="group",
                             title=title_override or (" & ".join(y_list) + f" by {x}"),
                             color_discrete_sequence=px.colors.qualitative.Safe,
                             text_auto=True)
                fig.update_traces(texttemplate="%{value:,.0f}", textposition="outside",
                                  textfont=dict(size=9,color="#374151"))
            else:
                fig = px.bar(df.head(40),x=x,y=y_col,color=color_use,
                             title=title_override or f"{y_col} by {x}",
                             text_auto=True,
                             color_discrete_sequence=px.colors.qualitative.Safe)
                fig.update_traces(texttemplate="%{value:,.0f}", textposition="outside",
                                  textfont=dict(size=10,color="#374151"))

        elif chart_type == "line":
            if len(y_list) > 1:
                fig = px.line(df, x=x, y=y_list, markers=True,
                              title=title_override or (" & ".join(y_list) + f" over {x}"),
                              color_discrete_sequence=px.colors.qualitative.Safe)
            else:
                fig = px.line(df,x=x,y=y_col,color=color_use,markers=True,
                              title=title_override or f"{y_col} over {x}",
                              color_discrete_sequence=[BRAND])
            fig.update_traces(mode="lines+markers+text",
                              texttemplate="%{y:,.0f}", textposition="top center",
                              textfont=dict(size=9,color="#374151"))

        elif chart_type == "area":
            if len(y_list) > 1:
                fig = px.area(df, x=x, y=y_list,
                              title=title_override or (" & ".join(y_list) + f" over {x}"),
                              color_discrete_sequence=px.colors.qualitative.Safe)
            else:
                fig = px.area(df,x=x,y=y_col,color=color_use,
                              title=title_override or f"{y_col} over {x}",
                              color_discrete_sequence=[BRAND])
            fig.update_traces(texttemplate="%{y:,.0f}", textposition="top center",
                              textfont=dict(size=9,color="#374151"))

        elif chart_type == "scatter":
            fig = px.scatter(df,x=x,y=y_col,color=color_use,
                             title=title_override or f"{y_col} vs {x}",
                             text=x if df[x].astype(str).str.len().max() <= 20 else None,
                             color_discrete_sequence=px.colors.qualitative.Safe)
            if x and df[x].astype(str).str.len().max() <= 20:
                fig.update_traces(textposition="top center", textfont=dict(size=9,color="#374151"))

        elif chart_type == "pie":
            fig = px.pie(df.head(15),names=x,values=y_col,
                         title=title_override or f"Share of {y_col} by {x}",
                         color_discrete_sequence=px.colors.qualitative.Safe)
            fig.update_traces(
                texttemplate="<b>%{label}</b><br>%{percent:.1%}<br>%{value:,.0f}",
                textposition="outside", textfont=dict(size=10),
                pull=[0.03]*min(15,len(df)),
            )

        elif chart_type == "donut":
            fig = px.pie(df.head(15),names=x,values=y_col,hole=0.45,
                         title=title_override or f"Share of {y_col} by {x}",
                         color_discrete_sequence=px.colors.qualitative.Safe)
            fig.update_traces(
                texttemplate="<b>%{label}</b><br>%{percent:.1%}",
                textposition="outside", textfont=dict(size=10),
            )

        elif chart_type == "pareto":
            orig = _coerce(pd.DataFrame(shared_dataset["records"]))
            if fcol and fcol in orig.columns and fval:
                orig = orig[orig[fcol].astype(str).isin(fval)]
            a = orig.groupby(x,dropna=False)[y_col].sum().sort_values(ascending=False).reset_index()
            a["cum%"] = a[y_col].cumsum()/a[y_col].sum()*100
            fig = go.Figure()
            fig.add_trace(go.Bar(x=a[x],y=a[y_col],name=y_col,marker_color=BRAND,
                                 text=[_fmt(v) for v in a[y_col]],
                                 textposition="outside",textfont=dict(size=9,color="#374151")))
            fig.add_trace(go.Scatter(x=a[x],y=a["cum%"],name="Cumulative %",
                                     yaxis="y2",mode="lines+markers+text",
                                     text=[f"{v:.0f}%" for v in a["cum%"]],
                                     textposition="top center",
                                     textfont=dict(size=9,color="#f59e0b"),
                                     line=dict(color="#f59e0b")))
            fig.add_hline(y=80,line_dash="dot",line_color="#ef4444",yref="y2",
                          annotation_text="80%")
            fig.update_layout(yaxis2=dict(overlaying="y",side="right",range=[0,118],title="Cum %"),
                              title=title_override or f"Pareto: {y_col} by {x}")

        elif chart_type == "box":
            orig = _coerce(pd.DataFrame(shared_dataset["records"]))
            fig = px.box(orig,x=x,y=y_col,color=color_use,
                         title=title_override or f"Distribution of {y_col} by {x}",
                         color_discrete_sequence=px.colors.qualitative.Safe,
                         points="outliers")
            fig.update_traces(boxmean=True)

        elif chart_type == "violin":
            orig = _coerce(pd.DataFrame(shared_dataset["records"]))
            fig = px.violin(orig,x=x,y=y_col,color=color_use,box=True,
                            title=title_override or f"Violin: {y_col} by {x}",
                            color_discrete_sequence=px.colors.qualitative.Safe)

        elif chart_type == "histogram":
            orig = _coerce(pd.DataFrame(shared_dataset["records"]))
            fig = px.histogram(orig,x=x or y_col,color=color_use,
                               title=title_override or f"Distribution: {x or y_col}",
                               color_discrete_sequence=[BRAND],
                               text_auto=True)
            fig.update_traces(texttemplate="%{y}", textposition="outside",
                              textfont=dict(size=9,color="#374151"))

        elif chart_type == "heatmap":
            good = [c for c in p.numeric_cols
                    if not (_series(df,c).is_monotonic_increasing and _series(df,c).nunique()==p.rows)]
            corr = _coerce(pd.DataFrame(shared_dataset["records"]))[good[:8]].corr(numeric_only=True).round(2)
            fig = px.imshow(corr,text_auto=True,color_continuous_scale="RdYlGn",
                            title=title_override or "Correlation Matrix")
            fig.update_traces(texttemplate="%{z:.2f}", textfont=dict(size=10))

        elif chart_type == "funnel":
            fig = px.funnel(df.head(20), x=y_col, y=x,
                            title=title_override or f"Funnel: {y_col} by {x}",
                            color_discrete_sequence=px.colors.qualitative.Safe)
            fig.update_traces(texttemplate="%{value:,.0f}", textposition="inside",
                              textfont=dict(size=10,color="#fff"))

        elif chart_type == "waterfall":
            vals = df[[x,y_col]].dropna().head(20)
            fig = go.Figure(go.Waterfall(
                name=y_col, orientation="v",
                x=vals[x].astype(str).tolist(),
                y=vals[y_col].tolist(),
                text=[_fmt(v) for v in vals[y_col]],
                textposition="outside",
                connector={"line":{"color":"#9ca3af"}},
                increasing={"marker":{"color":BRAND}},
                decreasing={"marker":{"color":"#ef4444"}},
            ))
            fig.update_layout(title=title_override or f"Waterfall: {y_col} by {x}")

        elif chart_type == "bubble":
            z_col = y_list[1] if len(y_list) > 1 else y_col
            fig = px.scatter(df, x=x, y=y_col, size=z_col,
                             color=color_use or x,
                             title=title_override or f"Bubble: {y_col} vs {x} (size={z_col})",
                             text=x,
                             color_discrete_sequence=px.colors.qualitative.Safe)
            fig.update_traces(textposition="top center", textfont=dict(size=9,color="#374151"))

        else:
            fig = px.scatter(title="Select a chart type")

        fig.update_layout(template="plotly_white",margin=dict(t=55,l=40,r=30,b=55),height=420)
        return fig, None

    except Exception as e:
        return None, f"Chart error: {e}"


# ── Preview callback ───────────────────────────────────────────────────────────

@dash.callback(
    Output("viz-custom","figure"),
    Output("viz-preview-store","data"),
    Input("viz-build","n_clicks"),
    State("shared-dataset","data"),
    State("viz-type","value"),
    State("viz-x","value"),
    State("viz-y","value"),
    State("viz-color","value"),
    State("viz-agg","value"),
    State("viz-fcol","value"),
    State("viz-fval","value"),
    State("viz-title-override","value"),
    prevent_initial_call=True,
)
def build_preview(_, shared_dataset, chart_type, x, y, color, agg, fcol, fval, title_override):
    fig, err = _build_figure(shared_dataset, chart_type, x, y, color, agg, fcol, fval, title_override)
    if err or fig is None:
        return {"data":[],"layout":{"title": err or "Error building chart"}}, None
    return fig, fig.to_json()


# ── Save chart to gallery ──────────────────────────────────────────────────────

@dash.callback(
    Output("viz-saved-charts","data", allow_duplicate=True),
    Output("viz-save-msg","children"),
    Input("viz-save","n_clicks"),
    State("viz-preview-store","data"),
    State("viz-saved-charts","data"),
    State("viz-title-override","value"),
    State("viz-type","value"),
    State("viz-x","value"),
    State("viz-y","value"),
    State("viz-agg","value"),
    prevent_initial_call=True,
)
def save_chart(_, fig_json, saved, title_override, chart_type, x, y, agg):
    if not fig_json:
        return saved, "⚠️ Build a preview first, then save."
    saved = saved or []
    auto_title = title_override or f"Chart {len(saved)+1}: {chart_type} — {y} by {x}"
    saved.append({"title": auto_title, "fig_json": fig_json,
                  "chart_type": chart_type, "x": x, "y": y, "agg": agg})
    return saved, f"✓ Saved — {len(saved)} chart(s) in gallery."


# ── Render gallery ─────────────────────────────────────────────────────────────

@dash.callback(
    Output("viz-gallery-section","children"),
    Input("viz-saved-charts","data"),
)
def render_gallery(saved):
    if not saved:
        return html.Div()
    import plotly.io as _pio
    cards = []
    for i, item in enumerate(saved):
        try:
            fig = _pio.from_json(item["fig_json"])
        except Exception:
            continue
        cards.append(html.Div([
            html.Div([
                html.Span(item["title"],
                          style={"fontWeight":"700","fontSize":"13px","color":"#374151"}),
                html.Button("✕ Remove", id={"type":"viz-remove","index":i},
                            n_clicks=0,
                            style={"marginLeft":"12px","padding":"2px 10px","fontSize":"11px",
                                   "background":"#fff","border":"1px solid #d1d5db",
                                   "borderRadius":"4px","cursor":"pointer","color":"#6b7280"}),
            ], style={"display":"flex","alignItems":"center","marginBottom":"8px"}),
            dcc.Graph(figure=fig, config=CFG),
        ], style={"background":"#fff","borderRadius":"10px","padding":"16px 18px",
                  "boxShadow":"0 1px 6px rgba(0,0,0,0.07)","border":"1px solid #e5e7eb",
                  "marginBottom":"16px"}))

    return html.Div([
        html.Div([
            html.Span(f"📁 Saved Charts Gallery ({len(saved)} charts)",
                      style={"fontWeight":"700","fontSize":"15px","color":"#1f2937"}),
            # Trigger the static hidden clear button by showing a styled label over it.
            # We DON'T re-render viz-clear-gallery here — it lives in the static layout.
            html.Label("🗑 Clear All", htmlFor="viz-clear-gallery",
                       style={"marginLeft":"14px","padding":"5px 14px","fontSize":"12px",
                              "background":"#fff","border":"1px solid #d1d5db",
                              "borderRadius":"6px","cursor":"pointer","color":"#6b7280",
                              "userSelect":"none"}),
        ], style={"display":"flex","alignItems":"center","marginBottom":"14px"}),
        *cards,
    ])


@dash.callback(
    Output("viz-saved-charts","data", allow_duplicate=True),
    Input("viz-clear-gallery","n_clicks"),
    prevent_initial_call=True,
)
def clear_gallery(_):
    return []


# ── Remove individual chart ────────────────────────────────────────────────────

@dash.callback(
    Output("viz-saved-charts","data", allow_duplicate=True),
    Input({"type":"viz-remove","index":ALL}, "n_clicks"),
    State("viz-saved-charts","data"),
    prevent_initial_call=True,
)
def remove_chart(n_clicks_list, saved):
    if not saved or not any(n_clicks_list):
        return saved
    triggered = ctx.triggered_id
    if triggered and "index" in triggered:
        idx = triggered["index"]
        if 0 <= idx < len(saved):
            saved = [s for i, s in enumerate(saved) if i != idx]
    return saved


# ── Export gallery to PDF ──────────────────────────────────────────────────────

@dash.callback(
    Output("viz-pdf-download","data"),
    Input("viz-export-pdf","n_clicks"),
    State("viz-saved-charts","data"),
    prevent_initial_call=True,
)
def export_pdf(_, saved):
    if not saved:
        return None
    pdf_bytes = _charts_to_pdf(saved)
    return dcc.send_bytes(lambda buf: buf.write(pdf_bytes), "dericbi_charts.pdf")


def _describe_chart(item):
    """Auto-generate a plain-language explanation for a saved chart."""
    ct  = item.get("chart_type","chart")
    x   = item.get("x") or "category"
    y   = item.get("y")
    agg = item.get("agg","sum")
    y_label = ", ".join(y) if isinstance(y, list) else (y or "values")

    templates = {
        "bar":       f"Bar chart showing the {agg} of {y_label} broken down by {x}. "
                     f"Each bar represents a distinct {x} value, making it easy to compare magnitudes across groups.",
        "line":      f"Line chart tracking {y_label} over {x}. "
                     f"The trend line reveals momentum, seasonality, and inflection points over time.",
        "area":      f"Area chart of {y_label} across {x}. "
                     f"Filled areas emphasise cumulative volume and highlight peaks and troughs.",
        "scatter":   f"Scatter plot comparing {y_label} against {x}. "
                     f"Each point is an observation — clusters and outliers indicate relationships or anomalies.",
        "pie":       f"Pie chart showing the proportional share of {y_label} by {x}. "
                     f"Each slice represents a segment's contribution to the total.",
        "donut":     f"Donut chart of {y_label} shares by {x}. "
                     f"The hollow centre draws attention to relative proportions between segments.",
        "pareto":    f"Pareto chart for {y_label} by {x}. "
                     f"Bars are ranked highest to lowest; the cumulative line identifies the 80/20 threshold — "
                     f"the vital few segments that drive the majority of value.",
        "box":       f"Box plot showing the statistical distribution of {y_label} across {x} groups. "
                     f"The box spans the interquartile range; whiskers show spread; dots are outliers.",
        "violin":    f"Violin plot of {y_label} by {x}. "
                     f"The width at each point shows data density, revealing multi-modal distributions that a box plot would hide.",
        "histogram": f"Histogram of {y_label} values. "
                     f"Bar heights show frequency — useful for understanding the underlying distribution and spotting skew.",
        "heatmap":   f"Correlation heatmap of numeric variables. "
                     f"Green cells indicate positive correlation, red indicates inverse correlation. "
                     f"Strong correlations (near ±1.0) suggest variables that move together.",
        "funnel":    f"Funnel chart of {y_label} by {x} stage. "
                     f"Narrowing width highlights drop-off between stages — ideal for conversion and pipeline analysis.",
        "waterfall": f"Waterfall chart of {y_label} by {x}. "
                     f"Rising bars are gains, falling bars are losses, making cumulative impact easy to trace.",
        "bubble":    f"Bubble chart comparing {y_label} across {x}. "
                     f"Bubble size adds a third dimension — larger bubbles represent higher values.",
    }
    return templates.get(ct, f"Chart showing {y_label} by {x}.")


def _charts_to_pdf(saved: list) -> bytes:
    """Render each saved chart as a PNG image and build a PDF with explanations."""
    import io
    import plotly.io as pio
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
        HRFlowable, PageBreak,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    styles = getSampleStyleSheet()
    BRAND_COLOR = colors.HexColor("#3e8865")

    title_style = ParagraphStyle(
        "ChartTitle", parent=styles["Heading2"],
        fontSize=13, textColor=BRAND_COLOR,
        spaceAfter=4, leading=16,
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["BodyText"],
        fontSize=10, leading=14, textColor=colors.HexColor("#374151"),
    )
    caption_style = ParagraphStyle(
        "Caption", parent=styles["BodyText"],
        fontSize=8, textColor=colors.HexColor("#9ca3af"), leading=11,
    )

    story = []

    # Cover title
    cover_style = ParagraphStyle(
        "Cover", parent=styles["Title"],
        fontSize=20, textColor=BRAND_COLOR, spaceAfter=8,
    )
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("DericBI — Chart Export", cover_style))
    story.append(Paragraph(
        f"Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}  |  "
        f"{len(saved)} chart(s)",
        caption_style,
    ))
    story.append(Spacer(1, 0.3*inch))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_COLOR))
    story.append(Spacer(1, 0.2*inch))

    W, H = A4
    img_width  = W - 3.6*cm   # full usable width
    img_height = img_width * 0.55  # ~16:9 aspect

    for i, item in enumerate(saved, 1):
        try:
            fig = pio.from_json(item["fig_json"])
        except Exception:
            continue

        # Render to PNG bytes
        try:
            img_bytes = fig.to_image(format="png", width=1200, height=660, scale=2)
        except Exception:
            # kaleido not available — skip image, keep text
            img_bytes = None

        story.append(Paragraph(f"{i}. {item['title']}", title_style))
        story.append(Spacer(1, 4))

        if img_bytes:
            img_buf = io.BytesIO(img_bytes)
            rl_img  = RLImage(img_buf, width=img_width, height=img_height)
            story.append(rl_img)
            story.append(Spacer(1, 8))

        desc = _describe_chart(item)
        story.append(Paragraph(desc, body_style))
        story.append(Spacer(1, 0.15*inch))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e5e7eb")))
        story.append(Spacer(1, 0.2*inch))

        # Page break every 2 charts to avoid crowding
        if i % 2 == 0 and i < len(saved):
            story.append(PageBreak())

    doc.build(story)
    return buf.getvalue()
