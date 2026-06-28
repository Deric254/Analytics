"""
Dashboard — uses DataProfile for fully dynamic, domain-agnostic auto-generation.
"""
import dash
from dash import html, dcc, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from services.insights_agent import DataProfile, _coerce, _series, _fmt, _pct, _chg

dash.register_page(__name__, path="/", name="Dashboard")

BRAND = "#3e8865"

def _kpi(title, value, sub="", color=BRAND):
    return html.Div([
        html.Div(title, style={"fontSize":"11px","fontWeight":"600","color":"#6b7280",
                               "textTransform":"uppercase","letterSpacing":"0.5px"}),
        html.Div(value, style={"fontSize":"26px","fontWeight":"700","color":color,
                               "lineHeight":"1.1","margin":"4px 0"}),
        html.Div(sub, style={"fontSize":"11px","color":"#9ca3af"}),
    ], style={"background":"#fff","borderRadius":"10px","padding":"16px 18px",
               "flex":"1","minWidth":"140px","boxShadow":"0 1px 6px rgba(0,0,0,0.07)",
               "border":"1px solid #e5e7eb"})

def _card(title, children, color=BRAND):
    return html.Div([
        html.Div(title, style={"fontSize":"13px","fontWeight":"700","color":"#374151",
                               "borderLeft":f"3px solid {color}","paddingLeft":"8px",
                               "marginBottom":"12px"}),
        *children,
    ], style={"background":"#fff","borderRadius":"10px","padding":"16px 18px",
               "boxShadow":"0 1px 6px rgba(0,0,0,0.07)","border":"1px solid #e5e7eb",
               "marginBottom":"16px"})

def _flag(icon, text, bg):
    return html.Div([
        html.Span(icon, style={"fontSize":"16px","marginRight":"8px"}),
        html.Span(text, style={"fontSize":"13px","color":"#374151"}),
    ], style={"background":bg,"borderRadius":"8px","padding":"10px 14px","marginBottom":"6px"})

CFG = {"displaylogo":False,"responsive":True}

layout = html.Div([
    html.Div([
        html.Div([
            html.H2("Dashboard", style={"margin":"0","fontSize":"22px","fontWeight":"700","color":"#1f2937"}),
            html.P(id="dash-subtitle",
                   style={"margin":"4px 0 0","color":"#6b7280","fontSize":"13px"}),
        ]),
        html.A(html.Button("→ Upload Data", style={
            "background":BRAND,"color":"#fff","border":"none","borderRadius":"6px",
            "padding":"8px 16px","cursor":"pointer","fontWeight":"600","fontSize":"13px",
        }), href="/ingestion"),
    ], style={"display":"flex","justifyContent":"space-between","alignItems":"flex-start",
              "marginBottom":"20px"}),

    dcc.Loading(html.Div(id="dash-kpis",
        style={"display":"flex","gap":"14px","flexWrap":"wrap","marginBottom":"20px"}), type="dot"),
    dcc.Loading(html.Div(id="dash-flags", style={"marginBottom":"16px"}), type="dot"),
    html.Div([
        html.Div(dcc.Loading(html.Div(id="dash-trend"), type="circle"),
                 style={"flex":"2","minWidth":"0"}),
        html.Div(dcc.Loading(html.Div(id="dash-top"),   type="circle"),
                 style={"flex":"1","minWidth":"220px"}),
    ], style={"display":"flex","gap":"16px","marginBottom":"16px","flexWrap":"wrap"}),
    html.Div([
        html.Div(dcc.Loading(html.Div(id="dash-dist"), type="circle"),
                 style={"flex":"1","minWidth":"0"}),
        html.Div(dcc.Loading(html.Div(id="dash-cat"),  type="circle"),
                 style={"flex":"1","minWidth":"0"}),
    ], style={"display":"flex","gap":"16px","flexWrap":"wrap"}),
    dcc.Loading(html.Div(id="dash-insights", style={"marginTop":"16px"}), type="dot"),
])


@dash.callback(
    Output("dash-subtitle",  "children"),
    Output("dash-kpis",      "children"),
    Output("dash-flags",     "children"),
    Output("dash-trend",     "children"),
    Output("dash-top",       "children"),
    Output("dash-dist",      "children"),
    Output("dash-cat",       "children"),
    Output("dash-insights",  "children"),
    Input("shared-dataset",  "data"),
)
def render(shared_dataset):
    welcome = html.Div([
        html.Div([
            html.H3("👋 Welcome to DericBI", style={"color":BRAND,"marginBottom":"8px"}),
            html.P("Get started:"),
            html.Ol([
                html.Li("Go to Ingestion → upload your CSV or Excel file"),
                html.Li("Return here — your dashboard auto-generates instantly"),
                html.Li("Use Insights for analysis, Visualization for charts, Reporting for exports"),
            ], style={"lineHeight":"2.2","fontSize":"14px"}),
        ], style={"background":"#fff","borderRadius":"10px","padding":"30px",
                  "boxShadow":"0 1px 6px rgba(0,0,0,0.07)","border":"1px solid #e5e7eb"})
    ])

    if not shared_dataset or not shared_dataset.get("records"):
        return ("Upload data to auto-generate your dashboard",
                [], html.Div(), html.Div(), html.Div(), html.Div(), html.Div(), welcome)

    df   = _coerce(pd.DataFrame(shared_dataset["records"]))
    p    = DataProfile(df)
    num  = p.value_col
    cat  = p.group_cols[0] if p.group_cols else None
    dc   = p.date_col
    fn   = shared_dataset.get("filename","dataset")

    subtitle = f"{fn}  |  {p.rows:,} rows × {p.cols_count} columns  |  Domain: {p.domain}"

    # ── KPIs ──────────────────────────────────────────────────────────────────
    missing = int(df.isna().sum().sum())
    dups    = int(df.duplicated().sum())
    total_c = p.rows * p.cols_count
    kpis    = [_kpi("Records", f"{p.rows:,}", f"{p.cols_count} columns")]
    kpis.append(_kpi("Completeness",
                     f"{_pct(total_c-missing, total_c)}",
                     f"{missing:,} missing",
                     color="#22c55e" if not missing else "#f59e0b"))
    kpis.append(_kpi("Duplicates", f"{dups:,}",
                     "clean" if not dups else "remove on Cleaning page",
                     color="#22c55e" if not dups else "#ef4444"))
    if num:
        s = _series(df, num)
        kpis.append(_kpi(f"Total {num}", _fmt(s.sum()), f"avg {_fmt(s.mean())}"))
        kpis.append(_kpi(f"Peak {num}",  _fmt(s.max()), f"low {_fmt(s.min())}"))

    # ── Health flags ───────────────────────────────────────────────────────────
    flags = []
    if not missing and not dups:
        flags.append(_flag("✅","Dataset is clean — no missing values or duplicates","rgba(34,197,94,0.08)"))
    if missing:
        w = df.isna().sum().idxmax()
        flags.append(_flag("⚠️",f"{missing:,} missing values — worst: '{w}'. Fix on Cleaning page.","rgba(245,158,11,0.08)"))
    if dups:
        flags.append(_flag("🔴",f"{dups:,} duplicate rows — remove on Cleaning page","rgba(239,68,68,0.08)"))
    if num:
        s = _series(df, num)
        if len(s) >= 4:
            q1,q3 = s.quantile(0.25),s.quantile(0.75)
            iqr   = q3-q1
            if iqr > 0:
                ext = s[s > q3+3*iqr]
                if not ext.empty:
                    flags.append(_flag("📊",f"{len(ext):,} extreme value(s) in '{num}' (up to {_fmt(ext.max())}) — verify on Insights","rgba(99,102,241,0.08)"))
    health = _card("Data Health", flags) if flags else html.Div()

    # ── Trend chart ────────────────────────────────────────────────────────────
    trend_section = html.Div()
    if dc and num:
        tmp = df.copy()
        tmp[dc] = pd.to_datetime(tmp[dc], errors="coerce")
        tmp = tmp.dropna(subset=[dc,num]).sort_values(dc)
        tmp[num] = pd.to_numeric(tmp[num], errors="coerce")
        days = (tmp[dc].max()-tmp[dc].min()).days
        tmp["_p"] = tmp[dc].dt.to_period("Q" if days>365 else "M" if days>60 else "W").astype(str)
        agg = tmp.groupby("_p")[num].sum().reset_index()
        agg.columns = ["Period", num]
        chg = _chg(agg[num].iloc[-1], agg[num].iloc[0]) if len(agg)>=2 else ""
        fig = px.area(agg, x="Period", y=num,
                      title=f"{num} over time  {chg}",
                      color_discrete_sequence=[BRAND])
        fig.update_traces(line_width=2)
        fig.update_layout(template="plotly_white",margin=dict(t=45,l=40,r=20,b=40),height=280)
        trend_section = _card(f"📈 {num} Trend",[dcc.Graph(figure=fig,config=CFG)])
    elif num:
        s = _series(df, num)
        fig = px.histogram(df, x=num, title=f"Distribution: {num}",
                           color_discrete_sequence=[BRAND])
        fig.update_layout(template="plotly_white",margin=dict(t=45,l=40,r=20,b=40),height=280)
        trend_section = _card(f"📊 {num} Distribution",[dcc.Graph(figure=fig,config=CFG)])

    # ── Top performers ─────────────────────────────────────────────────────────
    top_section = html.Div()
    if cat and num:
        agg = df.groupby(cat,dropna=False)[num].sum().sort_values(ascending=False).head(10).reset_index()
        grand = agg[num].sum()
        agg["share"] = (agg[num]/grand*100).round(1).astype(str)+"%"
        fig = px.bar(agg, x=num, y=cat, orientation="h",
                     title=f"Top {cat} by {num}",
                     text="share",
                     color=num,
                     color_continuous_scale=["#d1fae5",BRAND])
        fig.update_traces(textposition="outside")
        fig.update_layout(template="plotly_white",margin=dict(t=45,l=10,r=50,b=40),
                          height=280,yaxis={"categoryorder":"total ascending"},
                          coloraxis_showscale=False)
        top_section = _card(f"🏆 Top {cat}",[dcc.Graph(figure=fig,config=CFG)])

    # ── Distribution / spread ──────────────────────────────────────────────────
    dist_section = html.Div()
    good_nums = [c for c in p.numeric_cols
                 if not (_series(df,c).is_monotonic_increasing and _series(df,c).nunique()==p.rows)]
    if len(good_nums) >= 2:
        fig = px.box(df[good_nums[:5]], title="Spread of numeric columns",
                     color_discrete_sequence=px.colors.qualitative.Safe)
        fig.update_layout(template="plotly_white",margin=dict(t=45,l=30,r=10,b=40),height=260)
        dist_section = _card("📦 Numeric Spread",[dcc.Graph(figure=fig,config=CFG)])
    elif good_nums:
        fig = px.histogram(df,x=good_nums[0],color_discrete_sequence=[BRAND])
        fig.update_layout(template="plotly_white",margin=dict(t=30,l=30,r=10,b=30),height=260)
        dist_section = _card(f"📊 {good_nums[0]}",[dcc.Graph(figure=fig,config=CFG)])

    # ── Categorical pie ────────────────────────────────────────────────────────
    cat_section = html.Div()
    if cat:
        vc = df[cat].dropna().astype(str).value_counts().head(10).reset_index()
        vc.columns = [cat,"count"]
        fig = px.pie(vc, names=cat, values="count",
                     title=f"Breakdown: {cat}",
                     color_discrete_sequence=px.colors.qualitative.Safe)
        fig.update_traces(textinfo="label+percent",textposition="outside")
        fig.update_layout(margin=dict(t=45,l=0,r=0,b=0),height=260)
        cat_section = _card(f"🥧 {cat} Breakdown",[dcc.Graph(figure=fig,config=CFG)])

    # ── Auto-insights ──────────────────────────────────────────────────────────
    insights_list = []
    if num:
        s = _series(df, num)
        if len(s) >= 4:
            q1,q3 = s.quantile(0.25),s.quantile(0.75)
            iqr = q3-q1
            if iqr > 0:
                out = s[(s < q1-1.5*iqr)|(s > q3+1.5*iqr)]
                if not out.empty:
                    insights_list.append(f"⚠️ {len(out):,} outlier(s) in '{num}' detected by IQR method")
        cv = s.std()/s.mean() if s.mean() else 0
        if cv > 0.5:
            insights_list.append(f"📊 '{num}' has high variability (CV={cv:.2f}) — some records far outperform others")

    if cat and num:
        agg   = df.groupby(cat,dropna=False)[num].sum().sort_values(ascending=False).dropna()
        grand = agg.sum()
        if grand > 0 and len(agg) >= 2:
            top1 = agg.iloc[0]/grand*100
            insights_list.append(f"🏆 Top {cat}: '{agg.index[0]}' drives {top1:.1f}% of total {num}")
            if top1 >= 40:
                insights_list.append(f"🚨 Concentration risk: '{agg.index[0]}' accounts for {top1:.0f}% — monitor closely")

    if dc and num:
        tmp = df.copy()
        tmp[dc] = pd.to_datetime(tmp[dc],errors="coerce")
        tmp[num] = pd.to_numeric(tmp[num],errors="coerce")
        tmp = tmp.dropna(subset=[dc,num]).sort_values(dc)
        if len(tmp) >= 6:
            n = max(len(tmp)//4,1)
            first = tmp[num].iloc[:n].mean()
            last  = tmp[num].iloc[-n:].mean()
            if pd.notna(first) and pd.notna(last) and first != 0:
                chg = (last-first)/abs(first)*100
                arrow = "▲" if chg >= 0 else "▼"
                insights_list.append(f"{arrow} {num} moved {chg:+.1f}% from earliest to latest records")

    if len(p.numeric_cols) >= 2:
        good = [c for c in p.numeric_cols[:6]
                if not (_series(df,c).is_monotonic_increasing and _series(df,c).nunique()==p.rows)]
        if len(good) >= 2:
            corr = df[good].corr(numeric_only=True)
            best_r, best_pair = 0, None
            for i in range(len(good)):
                for j in range(i+1,len(good)):
                    v = abs(corr.iloc[i,j])
                    if not np.isnan(v) and v > best_r:
                        best_r = v
                        best_pair = (good[i],good[j],corr.iloc[i,j])
            if best_pair and best_r >= 0.6:
                a,b,r = best_pair
                insights_list.append(f"🔗 Strong correlation: '{a}' ↔ '{b}' (r={r:.2f})")

    insights_section = html.Div()
    if insights_list:
        insights_section = _card("💡 Auto-Insights", [
            html.Ul([
                html.Li(i, style={"marginBottom":"6px","fontSize":"13.5px","color":"#374151"})
                for i in insights_list
            ], style={"margin":"0","paddingLeft":"20px"})
        ])

    return subtitle, kpis, health, trend_section, top_section, dist_section, cat_section, insights_section
