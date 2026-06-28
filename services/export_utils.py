"""
Export utilities — fully dynamic, uses DataProfile column detection.
No hardcoded column names.
"""
import io
import zipfile
from datetime import datetime

import pandas as pd
import numpy as np
import plotly.io as pio
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak
)


def _fmt(v) -> str:
    try:
        f = float(v)
        if np.isnan(f): return "N/A"
        if abs(f) >= 1_000_000: return f"{f/1_000_000:,.2f}M"
        if abs(f) >= 1_000:     return f"{f:,.0f}"
        return f"{f:.2f}"
    except (TypeError, ValueError):
        return str(v)


def build_report_data(df: pd.DataFrame, source_name: str = "dataset") -> dict:
    """Build report data from any DataFrame — no hardcoded column assumptions."""
    from services.insights_agent import DataProfile, _coerce
    df   = _coerce(df)
    p    = DataProfile(df)
    rows, cols = df.shape
    missing    = int(df.isna().sum().sum())
    dups       = int(df.duplicated().sum())

    # Numeric summary — all numeric cols, skip ID-like
    num_rows = []
    for col in p.numeric_cols[:12]:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty: continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr    = q3 - q1
        out    = int(((s < q1-1.5*iqr)|(s > q3+1.5*iqr)).sum()) if iqr > 0 else 0
        num_rows.append({
            "Column":   col,
            "Count":    f"{len(s):,}",
            "Sum":      _fmt(s.sum()),
            "Mean":     _fmt(s.mean()),
            "Median":   _fmt(s.median()),
            "Std Dev":  _fmt(s.std()),
            "Min":      _fmt(s.min()),
            "Max":      _fmt(s.max()),
            "Outliers": str(out) if out else "—",
        })

    # Categorical summary
    cat_rows = []
    for col in p.cat_cols[:10]:
        s  = df[col].dropna().astype(str)
        vc = s.value_counts()
        cat_rows.append({
            "Column":       col,
            "Unique":       f"{s.nunique():,}",
            "Top value":    vc.index[0] if not vc.empty else "—",
            "Top count":    f"{int(vc.iloc[0]):,}" if not vc.empty else "—",
            "Top %":        f"{100*vc.iloc[0]/len(s):.1f}%" if not vc.empty else "—",
            "Missing":      f"{int(df[col].isna().sum()):,}",
        })

    # Executive findings — auto-generated from the data
    findings = _auto_findings(df, p, source_name)

    return {
        "overview": {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source":       source_name,
            "domain":       p.domain,
            "rows":         rows,
            "columns":      cols,
            "numeric_cols": len(p.numeric_cols),
            "cat_cols":     len(p.cat_cols),
            "date_cols":    len(p.date_cols),
            "missing":      missing,
            "missing_pct":  round(100*missing/(rows*cols) if rows*cols else 0, 2),
            "duplicates":   dups,
            "value_col":    p.value_col or "—",
            "group_cols":   ", ".join(p.group_cols) if p.group_cols else "—",
        },
        "findings":          findings,
        "numeric_summary":   pd.DataFrame(num_rows),
        "categorical_summary": pd.DataFrame(cat_rows),
        "sample_rows":       df.head(20),
    }


def _auto_findings(df, p, source_name) -> list[str]:
    """Generate 4-6 plain-English findings from any dataset."""
    from services.insights_agent import _series, _fmt, _pct, _chg
    findings = []
    num = p.value_col
    cat = p.group_cols[0] if p.group_cols else None
    rows, cols = df.shape
    missing = int(df.isna().sum().sum())
    dups    = int(df.duplicated().sum())

    # 1. Size & quality
    complete = 100*(rows*cols-missing)/(rows*cols) if rows*cols else 100
    qual = "complete" if not missing else f"{complete:.1f}% complete ({missing:,} gaps)"
    findings.append(
        f"The dataset contains {rows:,} records across {cols} columns "
        f"({p.numeric_cols.__len__()} numeric, {p.cat_cols.__len__()} categorical). "
        f"Data quality: {qual}."
        + (f" {dups:,} duplicate rows detected." if dups else "")
    )

    # 2. Key metric summary
    if num:
        s = _series(df, num)
        cv = s.std()/s.mean() if s.mean() else 0
        spread = ("highly variable" if cv > 0.5 else
                  "moderately variable" if cv > 0.2 else "consistent")
        findings.append(
            f"The primary metric '{num}' totals {_fmt(s.sum())} with an average of {_fmt(s.mean())} "
            f"and median of {_fmt(s.median())}. "
            f"Values are {spread} (CV={cv:.2f}), ranging from {_fmt(s.min())} to {_fmt(s.max())}."
        )

    # 3. Top performer
    if num and cat:
        agg   = df.groupby(cat,dropna=False)[num].sum().sort_values(ascending=False).dropna()
        grand = agg.sum()
        if grand > 0 and len(agg) >= 2:
            top1 = agg.iloc[0]
            share = 100*top1/grand
            findings.append(
                f"Top performer: '{agg.index[0]}' in '{cat}' accounts for "
                f"{_fmt(top1)} ({share:.1f}% of total {num})."
                + (" This represents significant concentration." if share >= 40 else "")
            )

    # 4. Trend
    if num and p.date_cols:
        dc  = p.date_cols[0]
        tmp = df.copy()
        tmp[dc] = pd.to_datetime(tmp[dc], errors="coerce")
        tmp[num] = pd.to_numeric(tmp[num], errors="coerce")
        tmp = tmp.dropna(subset=[dc,num]).sort_values(dc)
        if len(tmp) >= 6:
            n     = max(len(tmp)//4, 1)
            first = tmp[num].iloc[:n].mean()
            last  = tmp[num].iloc[-n:].mean()
            if pd.notna(first) and pd.notna(last) and first != 0:
                chg  = (last-first)/abs(first)*100
                word = "increased" if chg > 0 else "decreased"
                findings.append(
                    f"Trend: '{num}' has {word} by {abs(chg):.1f}% "
                    f"from the earliest to the most recent records."
                )

    # 5. Correlations
    good_nums = [c for c in p.numeric_cols[:8]
                 if not (_series(df,c).is_monotonic_increasing and _series(df,c).nunique()==rows)]
    if len(good_nums) >= 2:
        corr = df[good_nums].corr(numeric_only=True)
        best_r, best_pair = 0, None
        for i in range(len(good_nums)):
            for j in range(i+1,len(good_nums)):
                v = abs(corr.iloc[i,j])
                if not np.isnan(v) and v > best_r:
                    best_r = v
                    best_pair = (good_nums[i],good_nums[j],corr.iloc[i,j])
        if best_pair and best_r >= 0.5:
            a,b,r = best_pair
            direction = "positively" if r > 0 else "negatively"
            findings.append(
                f"Notable correlation: '{a}' and '{b}' are {direction} correlated (r={r:.2f}), "
                "suggesting these variables tend to move together."
            )

    return findings


def report_to_html(report_data: dict) -> str:
    ov = report_data["overview"]
    parts = [
        "<html><head><meta charset='utf-8'>",
        "<style>body{font-family:Segoe UI,sans-serif;margin:40px;color:#1f2937}"
        "h1{color:#3e8865}h2{color:#374151;border-bottom:2px solid #e5e7eb;padding-bottom:6px}"
        "table{border-collapse:collapse;width:100%}th{background:#f3f4f6;font-weight:700}"
        "td,th{border:1px solid #e5e7eb;padding:7px 10px;font-size:13px}"
        "tr:nth-child(even){background:#f9fafb}.finding{background:#f0fdf4;"
        "border-left:4px solid #3e8865;padding:12px 16px;margin:8px 0;border-radius:4px}</style>",
        "<title>DericBI Report</title></head><body>",
        f"<h1>Dataset Report — {ov['source']}</h1>",
        f"<p><b>Generated:</b> {ov['generated_at']}  |  "
        f"<b>Domain:</b> {ov['domain']}  |  "
        f"<b>Rows:</b> {ov['rows']:,}  |  <b>Columns:</b> {ov['columns']}</p>",
        f"<p><b>Completeness:</b> {100-ov['missing_pct']:.1f}%  |  "
        f"<b>Missing values:</b> {ov['missing']:,}  |  "
        f"<b>Duplicates:</b> {ov['duplicates']:,}</p>",
        f"<p><b>Key metric:</b> {ov['value_col']}  |  "
        f"<b>Main groups:</b> {ov['group_cols']}</p>",
        "<h2>Executive Findings</h2>",
    ]
    for f in report_data.get("findings", []):
        parts.append(f"<div class='finding'>{f}</div>")

    ns = report_data.get("numeric_summary", pd.DataFrame())
    if not ns.empty:
        parts.append("<h2>Numeric Column Statistics</h2>")
        parts.append(ns.to_html(index=False, border=0))

    cs = report_data.get("categorical_summary", pd.DataFrame())
    if not cs.empty:
        parts.append("<h2>Categorical Column Statistics</h2>")
        parts.append(cs.to_html(index=False, border=0))

    sr = report_data.get("sample_rows", pd.DataFrame())
    if not sr.empty:
        parts.append("<h2>Sample Records (first 20 rows)</h2>")
        parts.append(sr.to_html(index=False, border=0))

    parts.append("</body></html>")
    return "\n".join(parts)


def report_to_pdf(report_data: dict) -> bytes:
    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    story  = []
    ov     = report_data["overview"]

    story.append(Paragraph(f"Dataset Report — {ov['source']}", styles["Title"]))
    story.append(Spacer(1, 0.2*inch))
    for line in [
        f"Generated: {ov['generated_at']}",
        f"Domain: {ov['domain']}   |   Rows: {ov['rows']:,}   |   Columns: {ov['columns']}",
        f"Completeness: {100-ov['missing_pct']:.1f}%   |   Missing: {ov['missing']:,}   |   Duplicates: {ov['duplicates']:,}",
        f"Key metric: {ov['value_col']}   |   Main groups: {ov['group_cols']}",
    ]:
        story.append(Paragraph(line, styles["BodyText"]))

    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Executive Findings", styles["Heading2"]))
    for f in report_data.get("findings", []):
        story.append(Paragraph(f"• {f}", styles["BodyText"]))
        story.append(Spacer(1, 0.08*inch))

    def add_df_table(title, frame, max_rows=30):
        if frame is None or frame.empty: return
        story.append(Spacer(1, 0.15*inch))
        story.append(Paragraph(title, styles["Heading2"]))
        limited = frame.head(max_rows).fillna("—").astype(str)
        data    = [limited.columns.tolist()] + limited.values.tolist()
        tbl     = Table(data, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0),(-1,0), colors.lightgrey),
            ("GRID",       (0,0),(-1,-1), 0.4, colors.grey),
            ("FONTNAME",   (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0),(-1,-1), 7.5),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#f9fafb")]),
        ]))
        story.append(tbl)

    add_df_table("Numeric Column Statistics",     report_data.get("numeric_summary"))
    add_df_table("Categorical Column Statistics", report_data.get("categorical_summary"))
    add_df_table("Sample Records",               report_data.get("sample_rows"))

    doc.build(story)
    return buf.getvalue()


def df_to_excel(df: pd.DataFrame) -> bytes:
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="data")
    return out.getvalue()


def figures_to_zip(figures: list) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for i, fig in enumerate(figures, 1):
            zf.writestr(f"figure_{i}.html",
                        fig.to_html(full_html=True, include_plotlyjs="cdn"))
    return out.getvalue()


# Legacy alias used by reporting.py
build_exhaustive_report_data = build_report_data
report_data_to_html          = report_to_html
report_data_to_pdf_bytes     = report_to_pdf
dataframe_to_excel_bytes     = df_to_excel
