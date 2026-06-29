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
# reportlab imported lazily in report_to_pdf()


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
    """
    Generate intelligence-led findings from any dataset.
    Every finding answers: what does this mean and what should be done?
    """
    from services.insights_agent import _series, _fmt, _pct
    findings = []
    num  = p.value_col
    cat  = p.group_cols[0] if p.group_cols else None
    cat2 = p.group_cols[1] if len(p.group_cols) > 1 else None
    rows, cols_n = df.shape
    missing = int(df.isna().sum().sum())
    dups    = int(df.duplicated().sum())
    total_c = rows * cols_n

    # ── 1. Data integrity ─────────────────────────────────────────────────────
    if missing == 0 and dups == 0:
        findings.append(
            f"✅ Data integrity: {rows:,} records, fully complete — no missing values or duplicates. "
            "Analysis results are reliable."
        )
    else:
        parts = []
        if missing:
            pct  = 100 * missing / total_c
            worst = df.isna().sum().idxmax()
            parts.append(
                f"{missing:,} missing values ({pct:.1f}%) — worst in '{worst}' "
                f"({int(df[worst].isna().sum()):,} gaps). "
                "Fill or remove before drawing conclusions from this column."
            )
        if dups:
            parts.append(
                f"{dups:,} duplicate rows ({_pct(dups, rows)}) inflate totals. "
                "Remove duplicates on the Cleaning page."
            )
        findings.append("⚠️ Data quality issues: " + " | ".join(parts))

    # ── 2. Primary metric intelligence ───────────────────────────────────────
    if num:
        s  = _series(df, num)
        if not s.empty:
            total  = s.sum()
            mean   = s.mean()
            median = s.median()
            cv     = s.std() / mean if mean else 0

            if mean > median * 1.25:
                spread_note = (
                    f"Mean ({_fmt(mean)}) is significantly above median ({_fmt(median)}) — "
                    "a small number of high-value records drive the average up. "
                    "Focus retention on your top performers."
                )
            elif median > mean * 1.25:
                spread_note = (
                    f"Median ({_fmt(median)}) exceeds mean ({_fmt(mean)}) — "
                    "a few very low values drag the average down. "
                    "Review and address your lowest-performing records."
                )
            elif cv > 0.5:
                spread_note = (
                    f"High variability (CV={cv:.2f}) — performance is inconsistent. "
                    "Standardise processes to reduce this gap."
                )
            else:
                spread_note = f"Performance is consistent (CV={cv:.2f})."

            # 80/20 check
            top20 = s.nlargest(max(1, len(s) // 5))
            top20_share = top20.sum() / total if total else 0
            pareto_note = (
                f" Top 20% of records generate {_pct(top20.sum(), total)} of total {num} — "
                "protect these disproportionately."
                if top20_share >= 0.65 else ""
            )

            findings.append(
                f"📊 {num}: total {_fmt(total)}, average {_fmt(mean)}. "
                f"{spread_note}{pareto_note}"
            )

    # ── 3. Segment concentration & action ────────────────────────────────────
    if num and cat:
        agg   = df.groupby(cat, dropna=False)[num].sum().sort_values(ascending=False).dropna()
        grand = agg.sum()
        if grand > 0 and len(agg) >= 2:
            top_name  = agg.index[0]
            top_val   = agg.iloc[0]
            top_share = 100 * top_val / grand
            bot_name  = agg.index[-1]
            bot_val   = agg.iloc[-1]

            if top_share >= 40:
                action = (
                    f"🚨 Concentration risk: '{top_name}' drives {top_share:.0f}% of {num}. "
                    "Heavy dependence on one segment is a business risk. "
                    f"Invest in growing '{agg.index[1]}' (currently {_pct(agg.iloc[1], grand)}) "
                    "to reduce exposure."
                )
            else:
                gap = top_val - agg.iloc[1]
                action = (
                    f"🏆 '{top_name}' leads with {_pct(top_val, grand)} of {num}. "
                    f"Gap to second place ('{agg.index[1]}'): {_fmt(gap)}. "
                    "Identify what makes the top performer work and replicate it."
                )
            findings.append(action)

            # Bottom performer
            if len(agg) >= 3:
                bot_share = 100 * bot_val / grand
                findings.append(
                    f"🔻 Lowest: '{bot_name}' contributes only {_pct(bot_val, grand)} of {num}. "
                    + ("Consider exit, restructure, or targeted investment to understand the gap."
                       if bot_share < 5 else "Monitor — below-average but not critical yet.")
                )

    # ── 4. Trend with momentum and recommendation ─────────────────────────────
    if num and p.date_cols:
        dc  = p.date_cols[0]
        tmp = df.copy()
        tmp[dc] = pd.to_numeric(pd.to_datetime(tmp[dc], errors="coerce"), errors="coerce")
        tmp2 = df.copy()
        tmp2[dc] = pd.to_datetime(tmp2[dc], errors="coerce")
        tmp2[num] = pd.to_numeric(tmp2[num], errors="coerce")
        tmp2 = tmp2.dropna(subset=[dc, num]).sort_values(dc)

        if len(tmp2) >= 6:
            n     = max(len(tmp2) // 4, 1)
            first = tmp2[num].iloc[:n].mean()
            last  = tmp2[num].iloc[-n:].mean()
            prev  = tmp2[num].iloc[-(2*n):-n].mean() if len(tmp2) >= 3*n else first

            if pd.notna(first) and pd.notna(last) and first != 0:
                overall_chg = (last - first) / abs(first) * 100
                recent_chg  = (last - prev) / abs(prev) * 100 if pd.notna(prev) and prev != 0 else 0

                if overall_chg < -20:
                    rec = "Urgent investigation needed — compare winning vs losing periods to find the root cause."
                elif overall_chg < 0:
                    rec = "Declining trend — review what changed and whether it is structural or temporary."
                elif overall_chg > 20:
                    rec = "Strong growth — identify the driver and protect it. Avoid assuming it continues automatically."
                else:
                    rec = "Stable. Run a segment breakdown to find which sub-groups are growing vs declining."

                momentum = ""
                if abs(recent_chg) > 10:
                    momentum = (
                        f" Recent momentum: {recent_chg:+.1f}% in the latest quarter. "
                        + ("Accelerating — capitalise now." if recent_chg > 0 else "Decelerating — address immediately.")
                    )

                findings.append(
                    f"📈 Trend: {num} moved {overall_chg:+.1f}% from earliest to latest records. "
                    f"{rec}{momentum}"
                )

    # ── 5. Cross-segment opportunity ─────────────────────────────────────────
    if num and cat and cat2:
        pivot = df.groupby([cat, cat2], dropna=False)[num].sum().unstack(fill_value=0)
        best_combo = None
        best_val   = 0
        for c in pivot.index:
            for c2 in pivot.columns:
                v = pivot.loc[c, c2]
                if v > best_val:
                    best_val = v
                    best_combo = (c, c2)
        if best_combo:
            grand_total = df[num].sum() if num else 0
            findings.append(
                f"💡 Best combination: '{best_combo[0]}' × '{best_combo[1]}' "
                f"= {_fmt(best_val)} ({_pct(best_val, grand_total)} of total). "
                "This cross-segment generates disproportionate value — prioritise it."
            )

    # ── 6. Correlation → actionable relationship ──────────────────────────────
    good_nums = [c for c in p.numeric_cols[:8]
                 if _series(df, c).std() > 0
                 and not (_series(df,c).is_monotonic_increasing and _series(df,c).nunique()==rows)]
    if len(good_nums) >= 2:
        corr     = df[good_nums].corr(numeric_only=True)
        best_r, best_pair = 0, None
        for i in range(len(good_nums)):
            for j in range(i+1, len(good_nums)):
                v = abs(corr.iloc[i, j])
                if not np.isnan(v) and v > best_r:
                    best_r     = v
                    best_pair  = (good_nums[i], good_nums[j], corr.iloc[i, j])
        if best_pair and best_r >= 0.5:
            a, b, r = best_pair
            direction = "increases" if r > 0 else "decreases"
            strength  = "strongly" if best_r >= 0.8 else "moderately"
            findings.append(
                f"🔗 When '{a}' rises, '{b}' {strength} {direction} (r={r:.2f}). "
                + ("Use this lever — improving one drives the other."
                   if r > 0 else
                   "Trade-off detected — improving one may reduce the other. Balance carefully.")
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
    # Lazy import — keeps startup fast
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    )
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
