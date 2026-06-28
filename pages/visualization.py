"""
Visualization — 7 auto-generated business charts using DataProfile.
Custom builder is secondary. Loading spinner visible between click and output.
"""
import dash
from dash import html, dcc, Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
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
            html.Div([
                html.Div([
                    html.Label("Chart type", style={"fontSize":"12px","fontWeight":"600","color":"#6b7280"}),
                    dcc.Dropdown(id="viz-type", value="bar", clearable=False, options=[
                        {"label":"Bar",        "value":"bar"},
                        {"label":"Line",       "value":"line"},
                        {"label":"Area",       "value":"area"},
                        {"label":"Scatter",    "value":"scatter"},
                        {"label":"Pie",        "value":"pie"},
                        {"label":"Pareto",     "value":"pareto"},
                        {"label":"Box",        "value":"box"},
                        {"label":"Histogram",  "value":"histogram"},
                        {"label":"Heatmap",    "value":"heatmap"},
                    ]),
                ], style={"flex":"1","minWidth":"120px"}),
                html.Div([
                    html.Label("X axis", style={"fontSize":"12px","fontWeight":"600","color":"#6b7280"}),
                    dcc.Dropdown(id="viz-x", placeholder="X column"),
                ], style={"flex":"1","minWidth":"120px"}),
                html.Div([
                    html.Label("Y axis", style={"fontSize":"12px","fontWeight":"600","color":"#6b7280"}),
                    dcc.Dropdown(id="viz-y", placeholder="Y column"),
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

            html.Button("Build Chart →", id="viz-build", n_clicks=0, style={
                "padding":"8px 20px","background":BRAND,"color":"#fff","border":"none",
                "borderRadius":"6px","cursor":"pointer","fontWeight":"700","fontSize":"13px",
            }),

            dcc.Loading(
                dcc.Graph(id="viz-custom",
                          figure={"data":[],"layout":{"title":"Configure and click Build Chart"}},
                          config=CFG,style={"marginTop":"16px"}),
                type="dot"),
        ], style={"padding":"0 0 16px"}),
    ], style={"background":"#fff","borderRadius":"10px","padding":"0 18px",
               "boxShadow":"0 1px 6px rgba(0,0,0,0.07)","border":"1px solid #e5e7eb"}),
])


# ── Auto charts ───────────────────────────────────────────────────────────────

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

    # KPI strip — fully dynamic from DataProfile
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
        fig = px.area(agg, x="Period", y=num, title=f"{num} over time  {chg}",
                      color_discrete_sequence=[BRAND])
        fig.update_traces(line_width=2.5)
        fig.update_layout(template="plotly_white",margin=dict(t=50,l=40,r=20,b=50),height=300)
        charts.append(_card(f"📈 {num} Trend",[dcc.Graph(figure=fig,config=CFG)]))

    # 2. Top performers
    if cat and num:
        agg = df.groupby(cat,dropna=False)[num].sum().sort_values(ascending=False).head(12).reset_index()
        grand = agg[num].sum()
        agg["pct"] = (agg[num]/grand*100).round(1).astype(str)+"%"
        fig = px.bar(agg, x=num, y=cat, orientation="h",
                     title=f"Top {cat} by {num}",
                     text="pct", color=num,
                     color_continuous_scale=["#d1fae5",BRAND])
        fig.update_traces(textposition="outside")
        fig.update_layout(template="plotly_white",margin=dict(t=50,l=10,r=60,b=40),
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
        fig.add_trace(go.Bar(x=agg[cat], y=agg[num], name=num, marker_color=BRAND))
        fig.add_trace(go.Scatter(x=agg[cat], y=agg["cum%"], name="Cumulative %",
                                 yaxis="y2", mode="lines+markers",
                                 line=dict(color="#f59e0b",width=2.5)))
        fig.add_hline(y=80, line_dash="dot", line_color="#ef4444",
                      annotation_text="80%", yref="y2")
        fig.update_layout(
            title=f"Pareto 80/20 — {num} by {cat}",
            yaxis=dict(title=num),
            yaxis2=dict(title="Cumulative %",overlaying="y",side="right",range=[0,108]),
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
                     color_discrete_sequence=px.colors.qualitative.Safe)
        fig.update_layout(template="plotly_white",height=320,
                          margin=dict(t=50,l=40,r=20,b=60))
        charts.append(_card(f"⚖️ Comparison: {cat} × {cat2}",[dcc.Graph(figure=fig,config=CFG)]))
    elif cat and num:
        agg = df.groupby(cat,dropna=False)[num].sum().reset_index()
        fig = px.pie(agg, names=cat, values=num, title=f"Share of {num} by {cat}",
                     color_discrete_sequence=px.colors.qualitative.Safe)
        fig.update_traces(textinfo="label+percent",textposition="outside")
        fig.update_layout(margin=dict(t=50,l=0,r=0,b=0),height=300)
        charts.append(_card(f"🥧 {cat} Market Share",[dcc.Graph(figure=fig,config=CFG)]))

    # 5. Revenue vs Cost vs Margin (only if both found via DataProfile keywords)
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
        fig.add_trace(go.Bar(name="Revenue",x=agg[cat],y=agg["Revenue"],marker_color=BRAND))
        fig.add_trace(go.Bar(name="Cost",   x=agg[cat],y=agg["Cost"],   marker_color="#f87171"))
        fig.add_trace(go.Scatter(name="Margin %",x=agg[cat],y=agg["Margin%"],
                                 mode="lines+markers+text",yaxis="y2",
                                 text=agg["Margin%"].astype(str)+"%",
                                 textposition="top center",
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

    # 6. Correlation heatmap — only non-ID numeric cols
    good_nums = [c for c in p.numeric_cols
                 if not (_series(df,c).is_monotonic_increasing and _series(df,c).nunique()==p.rows)]
    if len(good_nums) >= 3:
        corr = df[good_nums[:8]].corr(numeric_only=True).round(2)
        fig  = px.imshow(corr, text_auto=True, color_continuous_scale="RdYlGn",
                         zmin=-1, zmax=1,
                         title="Correlation Matrix — which numbers move together?")
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


# ── Custom builder ────────────────────────────────────────────────────────────

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


@dash.callback(
    Output("viz-custom","figure"),
    Input("viz-build","n_clicks"),
    State("shared-dataset","data"),
    State("viz-type","value"),
    State("viz-x","value"),
    State("viz-y","value"),
    State("viz-color","value"),
    State("viz-agg","value"),
    State("viz-fcol","value"),
    State("viz-fval","value"),
    prevent_initial_call=True,
)
def build_custom(_, shared_dataset, chart_type, x, y, color, agg, fcol, fval):
    if not shared_dataset or not shared_dataset.get("records"):
        return {"data":[],"layout":{"title":"No data loaded"}}

    df = _coerce(pd.DataFrame(shared_dataset["records"]))
    p  = DataProfile(df)

    if fcol and fcol in df.columns and fval:
        df = df[df[fcol].astype(str).isin(fval)]
    if df.empty:
        return {"data":[],"layout":{"title":"No rows after filter"}}

    # Fallback to DataProfile defaults
    x = x or (p.group_cols[0] if p.group_cols else df.columns[0])
    y = y or p.value_col or p.numeric_cols[0] if p.numeric_cols else None
    color_use = color if color and color in df.columns else None

    if not y:
        return {"data":[],"layout":{"title":"Select a Y axis column"}}

    # Aggregate if groupby meaningful
    if x and x in df.columns and y and y in df.columns and agg:
        num_check = pd.to_numeric(df[y], errors="coerce")
        if num_check.notna().mean() >= 0.5:
            agg_map = {"sum":"sum","mean":"mean","count":"size","max":"max","min":"min"}
            fn = agg_map.get(agg,"sum")
            if fn == "size":
                df_agg = df.groupby(x,dropna=False).size().reset_index(name="Count")
                y = "Count"
            else:
                df_agg = df.groupby(x,dropna=False)[y].agg(fn).reset_index()
            df = df_agg

    try:
        if chart_type == "bar":
            fig = px.bar(df.head(40),x=x,y=y,color=color_use,
                         title=f"{y} by {x}",text_auto=True,
                         color_discrete_sequence=px.colors.qualitative.Safe)
        elif chart_type == "line":
            fig = px.line(df,x=x,y=y,color=color_use,
                          title=f"{y} over {x}",markers=True,
                          color_discrete_sequence=[BRAND])
        elif chart_type == "area":
            fig = px.area(df,x=x,y=y,color=color_use,
                          title=f"{y} over {x}",
                          color_discrete_sequence=[BRAND])
        elif chart_type == "scatter":
            fig = px.scatter(df,x=x,y=y,color=color_use,
                             title=f"{y} vs {x}",
                             color_discrete_sequence=px.colors.qualitative.Safe)
        elif chart_type == "pie":
            fig = px.pie(df.head(15),names=x,values=y,
                         title=f"Share of {y} by {x}",
                         color_discrete_sequence=px.colors.qualitative.Safe)
        elif chart_type == "pareto":
            raw = pd.DataFrame(shared_dataset["records"])
            raw = _coerce(raw)
            if fcol and fcol in raw.columns and fval:
                raw = raw[raw[fcol].astype(str).isin(fval)]
            a = raw.groupby(x,dropna=False)[y].sum().sort_values(ascending=False).reset_index()
            a["cum%"] = a[y].cumsum()/a[y].sum()*100
            fig = go.Figure()
            fig.add_trace(go.Bar(x=a[x],y=a[y],name=y,marker_color=BRAND))
            fig.add_trace(go.Scatter(x=a[x],y=a["cum%"],name="Cumulative %",
                                     yaxis="y2",mode="lines+markers",
                                     line=dict(color="#f59e0b")))
            fig.add_hline(y=80,line_dash="dot",line_color="#ef4444",yref="y2")
            fig.update_layout(yaxis2=dict(overlaying="y",side="right",range=[0,108],title="Cum %"),
                              title=f"Pareto: {y} by {x}")
        elif chart_type == "box":
            orig = _coerce(pd.DataFrame(shared_dataset["records"]))
            fig = px.box(orig,x=x,y=y,color=color_use,
                         title=f"Distribution of {y} by {x}",
                         color_discrete_sequence=px.colors.qualitative.Safe)
        elif chart_type == "histogram":
            orig = _coerce(pd.DataFrame(shared_dataset["records"]))
            fig = px.histogram(orig,x=x or y,color=color_use,
                               title=f"Distribution: {x or y}",
                               color_discrete_sequence=[BRAND])
        elif chart_type == "heatmap":
            good = [c for c in p.numeric_cols
                    if not (_series(df,c).is_monotonic_increasing and _series(df,c).nunique()==p.rows)]
            corr = _coerce(pd.DataFrame(shared_dataset["records"]))[good[:8]].corr(numeric_only=True).round(2)
            fig = px.imshow(corr,text_auto=True,color_continuous_scale="RdYlGn",
                            title="Correlation Matrix")
        else:
            fig = px.scatter(title="Select a chart type")

        fig.update_layout(template="plotly_white",margin=dict(t=50,l=40,r=20,b=50),height=400)
        return fig
    except Exception as e:
        return {"data":[],"layout":{"title":f"Chart error: {e}"}}
