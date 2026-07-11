"""
Export utilities — fully dynamic, uses DataProfile column detection.
No hardcoded column names.
"""
import io
from datetime import datetime

import pandas as pd
import numpy as np
import plotly.io as pio
# reportlab imported lazily in report_to_pdf()


def _fmt(v) -> str:
    """Always 2 decimal places, comma-separated thousands. Clean and consistent."""
    try:
        f = float(v)
        if np.isnan(f): return "N/A"
        return f"{f:,.2f}"
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

            # 80/20 check — only meaningful when all values share the same sign
            # as the total; mixed positive/negative data can push a "share"
            # figure above 100% or negative, which is accurate but unreadable.
            top20 = s.nlargest(max(1, len(s) // 5))
            all_same_sign = (s >= 0).all() or (s <= 0).all()
            top20_share = (top20.sum() / total) if (total and all_same_sign) else 0
            pareto_note = (
                f" Top 20% of records generate {_pct(top20.sum(), total)} of total {num} — "
                "protect these disproportionately."
                if (all_same_sign and top20_share >= 0.65) else ""
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


def _make_page_decorator(brand_name="DericBI"):
    """Returns a canvas callback that draws a slim brand header rule and a
    footer with page numbers — applied to every page, keeps the report
    looking branded without adding bulky logo images that bloat file size.
    """
    from reportlab.lib import colors
    from reportlab.lib.units import inch

    brand_green = colors.HexColor("#3e8865")
    light_grey  = colors.HexColor("#9ca3af")

    def _draw(canvas, doc):
        canvas.saveState()
        w, h = doc.pagesize
        # top accent rule
        canvas.setStrokeColor(brand_green)
        canvas.setLineWidth(2)
        canvas.line(doc.leftMargin, h - 0.32*inch, w - doc.rightMargin, h - 0.32*inch)
        # footer: brand left, page number right
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(light_grey)
        canvas.drawString(doc.leftMargin, 0.3*inch, brand_name)
        canvas.drawRightString(w - doc.rightMargin, 0.3*inch, f"Page {doc.page}")
        canvas.restoreState()

    return _draw


def _decode_plotly_array(v):
    """
    Plotly 6.x compresses numeric trace arrays into {'dtype':..., 'bdata': base64}
    when a figure is round-tripped through to_json()/from_json(). Decode that back
    into a plain list so downstream analysis sees real numbers, not a dict.
    """
    if v is None:
        return []
    if isinstance(v, dict) and "bdata" in v:
        import base64
        raw = base64.b64decode(v["bdata"])
        dtype = v.get("dtype", "f8")
        return np.frombuffer(raw, dtype=dtype).tolist()
    try:
        return list(v)
    except TypeError:
        return [v]


def _analyze_figure(fig_json) -> str:
    """
    Generic analyst-style read on a Plotly figure — works for any chart the
    builder can produce, without needing the original DataFrame. Looks at
    the figure's own trace data (what's actually plotted) and reasons about
    leaders, gaps, concentration, and trend direction.
    """
    import plotly.io as pio
    try:
        fig = pio.from_json(fig_json) if isinstance(fig_json, str) else fig_json
        traces = fig.data
        if not traces:
            return "No plotted data to analyse."

        t0 = traces[0]
        ttype = getattr(t0, "type", "")

        # Pareto: bar + cumulative-% line
        if len(traces) >= 2 and ttype == "bar" and getattr(traces[1], "type", "") == "scatter":
            ys = [v for v in _decode_plotly_array(t0.y) if v is not None]
            xs = _decode_plotly_array(t0.x)
            if xs and ys:
                total = sum(ys)
                pairs = sorted(zip(xs, ys), key=lambda p: p[1], reverse=True)
                cum, n80 = 0, 0
                for _, v in pairs:
                    cum += v
                    n80 += 1
                    if total and cum / total >= 0.8:
                        break
                pct_of_cats = 100 * n80 / len(pairs) if pairs else 0
                return (f"Top {n80} of {len(pairs)} categories ({pct_of_cats:.0f}%) drive 80% of the total. "
                        f"'{pairs[0][0]}' alone contributes {100*pairs[0][1]/total:.0f}%. "
                        + ("Heavy concentration — prioritise and protect these few." if pct_of_cats <= 30
                           else "Fairly distributed — no single segment dominates."))

        if ttype == "bar" and len(traces) == 1:
            xs = _decode_plotly_array(t0.x)
            ys = _decode_plotly_array(t0.y)
            pairs = [(x, y) for x, y in zip(xs, ys) if y is not None]
            if pairs:
                pairs.sort(key=lambda p: p[1], reverse=True)
                total = sum(p[1] for p in pairs)
                top_name, top_val = pairs[0]
                share = 100 * top_val / total if total else 0
                line = f"'{top_name}' leads at {_fmt(top_val)} ({share:.0f}% of total)."
                if len(pairs) > 1:
                    second_name, second_val = pairs[1]
                    line += f" Gap to '{second_name}': {_fmt(top_val - second_val)}."
                if len(pairs) >= 3:
                    bot_name, bot_val = pairs[-1]
                    line += f" Weakest performer: '{bot_name}' at {_fmt(bot_val)}."
                if share >= 40:
                    line += " Concentration risk — heavy reliance on the top segment."
                return line

        if ttype == "pie":
            labels = _decode_plotly_array(t0.labels)
            values = _decode_plotly_array(t0.values)
            pairs = [(l, v) for l, v in zip(labels, values) if v is not None]
            if pairs:
                total = sum(p[1] for p in pairs)
                pairs.sort(key=lambda p: p[1], reverse=True)
                top_name, top_val = pairs[0]
                share = 100 * top_val / total if total else 0
                note = "high concentration — a single segment dominates" if share >= 40 else "reasonably balanced spread"
                return f"'{top_name}' holds {share:.0f}% of the share — {note}."

        if ttype in ("scatter", "scattergl") and "lines" in (getattr(t0, "mode", "") or ""):
            ys = [v for v in _decode_plotly_array(t0.y) if v is not None]
            if len(ys) >= 2:
                first, last = ys[0], ys[-1]
                chg = (last - first) / abs(first) * 100 if first else 0
                if chg > 5:
                    verdict = "Upward trend — momentum is favourable; protect and reinforce the current drivers."
                elif chg < -5:
                    verdict = "Downward trend — investigate what changed before the next reporting cycle."
                else:
                    verdict = "Broadly flat — stable, but watch for the next inflection point."
                return f"Moved {chg:+.1f}% from start to end of the series. {verdict}"

        if ttype == "scatter" and (getattr(t0, "mode", "") or "") == "markers":
            xs = [v for v in _decode_plotly_array(t0.x) if v is not None]
            ys = [v for v in _decode_plotly_array(t0.y) if v is not None]
            if len(xs) >= 3 and len(ys) >= 3:
                try:
                    corr = pd.Series(xs).astype(float).corr(pd.Series(ys).astype(float))
                    if pd.notna(corr) and abs(corr) >= 0.5:
                        direction = "positive" if corr > 0 else "negative"
                        return f"Clear {direction} relationship between the two variables (r≈{corr:.2f}) — usable as a lever."
                except Exception:
                    pass
            return "Spread shows the relationship between these two variables — look for clusters or outliers."

        if ttype == "box":
            return "Distribution by group — wide boxes or many outlier points flag inconsistent performance worth standardising."

        if ttype == "histogram":
            return "Frequency distribution — skew or multiple peaks usually signal distinct sub-populations worth segmenting separately."

        if ttype == "heatmap":
            return "Correlation matrix — cells near +1/-1 mark variable pairs worth investigating as cause-and-effect candidates."

    except Exception:
        pass
    return "Review for leaders, laggards, and concentration relevant to this metric."


def _ai_executive_summary(report_data: dict) -> str:
    """
    Ask the AI assistant to turn the rule-based findings and chart insights
    into a short, cohesive business narrative — 3-5 sentences, no jargon,
    grounded only in the facts already computed (no hallucination risk since
    the AI is given the exact numbers to work from, not raw data).
    Falls back to a plain join of findings if no AI key is configured or the
    call fails for any reason — the report never breaks.
    """
    try:
        from services.ai_assistant import ask as ai_ask
    except Exception:
        return " ".join(report_data.get("findings", [])[:3])

    ov       = report_data.get("overview", {})
    findings = report_data.get("findings", [])
    charts   = report_data.get("charts", []) or []

    chart_notes = []
    for item in charts[:6]:
        fig_json = item.get("fig_json")
        if fig_json:
            chart_notes.append(_analyze_figure(fig_json))

    context_lines = [
        f"Dataset: {ov.get('source','data')}, domain: {ov.get('domain','general')}, "
        f"{ov.get('rows',0):,} records.",
        "Computed findings: " + " | ".join(findings[:6]),
    ]
    if chart_notes:
        context_lines.append("Chart-level observations: " + " | ".join(chart_notes))

    prompt = (
        "Write a short executive summary (3-5 sentences, plain business language, "
        "no bullet points, no headers) for a business report, based ONLY on these "
        "computed facts — do not invent numbers not given here:\n\n"
        + "\n".join(context_lines)
    )

    try:
        narrative = ai_ask(prompt, df=None)
        if narrative and len(narrative.strip()) > 20 and "No AI API key" not in narrative:
            return narrative.strip()
    except Exception:
        pass

    return " ".join(findings[:4]) if findings else "No significant findings to report."


def report_to_pdf(report_data: dict) -> bytes:
    """
    Business-oriented PDF report. Executive findings are the centerpiece —
    presented prominently, before the supporting data tables.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, HRFlowable
    )

    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=0.6*inch, rightMargin=0.6*inch,
        topMargin=0.5*inch, bottomMargin=0.5*inch,
    )
    base_styles = getSampleStyleSheet()
    ov = report_data["overview"]

    brand_green = colors.HexColor("#3e8865")
    text_grey   = colors.HexColor("#374151")
    light_grey  = colors.HexColor("#9ca3af")

    title_style = ParagraphStyle(
        "DericTitle", parent=base_styles["Title"],
        textColor=brand_green, fontSize=22, spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DericSubtitle", parent=base_styles["BodyText"],
        textColor=light_grey, fontSize=10, spaceAfter=14,
    )
    section_style = ParagraphStyle(
        "DericSection", parent=base_styles["Heading2"],
        textColor=text_grey, fontSize=14, spaceBefore=14, spaceAfter=8,
        borderColor=brand_green, borderWidth=0, leftIndent=0,
    )
    finding_style = ParagraphStyle(
        "DericFinding", parent=base_styles["BodyText"],
        textColor=text_grey, fontSize=10.5, leading=15,
        leftIndent=10, spaceAfter=8,
        borderColor=brand_green, borderWidth=0,
    )
    meta_style = ParagraphStyle(
        "DericMeta", parent=base_styles["BodyText"],
        textColor=text_grey, fontSize=9.5, leading=14,
    )

    story = []

    # ── Cover header ──────────────────────────────────────────────────────────
    story.append(Paragraph(f"Business Report — {ov['source']}", title_style))
    story.append(Paragraph(
        f"Generated {ov['generated_at']}  ·  Domain: {ov['domain'].title()}  ·  "
        f"{ov['rows']:,} records analysed",
        subtitle_style,
    ))
    story.append(HRFlowable(width="100%", thickness=1.2, color=brand_green, spaceAfter=14))

    # ── Key facts strip ───────────────────────────────────────────────────────
    facts = [
        ["Rows", f"{ov['rows']:,}", "Columns", f"{ov['columns']}"],
        ["Completeness", f"{100-ov['missing_pct']:.1f}%", "Duplicates", f"{ov['duplicates']:,}"],
        ["Key metric", ov["value_col"], "Main groups", ov["group_cols"]],
    ]
    fact_table = Table(facts, colWidths=[1.2*inch, 1.7*inch, 1.2*inch, 1.7*inch])
    fact_table.setStyle(TableStyle([
        ("FONTNAME",   (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",   (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR",  (0, 0), (-1, -1), text_grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("LINEBELOW",  (0, 0), (-1, -2), 0.4, colors.HexColor("#f3f4f6")),
    ]))
    story.append(fact_table)
    story.append(Spacer(1, 0.15*inch))

    # ── AI Executive Summary — the centerpiece, written in business language ──
    story.append(Paragraph("Executive Summary", section_style))
    story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#e5e7eb"), spaceAfter=10))
    narrative = _ai_executive_summary(report_data)
    story.append(Paragraph(narrative, finding_style))
    story.append(Spacer(1, 0.12*inch))

    # ── Key Points — compact, grounded, backs up the narrative above ─────────
    findings = report_data.get("findings", [])
    if findings:
        story.append(Paragraph("Key Points", ParagraphStyle(
            "DericKeyPoints", parent=base_styles["Heading3"],
            textColor=text_grey, fontSize=11, spaceBefore=4, spaceAfter=6,
        )))
        for f in findings[:6]:
            clean = f.encode("ascii", "ignore").decode("ascii").strip() if any(ord(c) > 127 for c in f[:2]) else f
            clean = clean if clean else f
            story.append(Paragraph(f"•&nbsp; {clean}", ParagraphStyle(
                "DericBullet", parent=base_styles["BodyText"],
                textColor=text_grey, fontSize=9.5, leading=13,
                leftIndent=10, spaceAfter=3,
            )))

    story.append(Spacer(1, 0.15*inch))

    # ── Visual Analysis — every chart (auto + custom-built), each with its own
    # analyst-level read, branded consistently with the rest of the report ──
    charts = report_data.get("charts") or []
    if charts:
        import plotly.io as pio
        from reportlab.platypus import Image, KeepTogether

        chart_title_style = ParagraphStyle(
            "DericChartTitle", parent=base_styles["Heading3"],
            textColor=text_grey, fontSize=11, spaceBefore=2, spaceAfter=4,
        )
        insight_style = ParagraphStyle(
            "DericInsight", parent=base_styles["BodyText"],
            textColor=text_grey, fontSize=9.5, leading=13,
            leftIndent=8, spaceAfter=4,
            borderColor=brand_green, borderWidth=0,
        )
        insight_label_style = ParagraphStyle(
            "DericInsightLabel", parent=base_styles["BodyText"],
            textColor=brand_green, fontSize=8.5, leading=11,
            spaceAfter=2, fontName="Helvetica-Bold",
        )

        story.append(Paragraph(f"Visual Analysis ({len(charts)} charts)", section_style))
        story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#e5e7eb"), spaceAfter=10))

        avail_w = doc.width
        for item in charts:
            label    = item.get("label", "Chart")
            fig_json = item.get("fig_json")
            if not fig_json:
                continue
            try:
                fig = pio.from_json(fig_json) if isinstance(fig_json, str) else fig_json
                fig.update_layout(
                    margin=dict(l=40, r=20, t=40, b=36),
                    paper_bgcolor="white", plot_bgcolor="white",
                    font=dict(size=11),
                )
                img_bytes = pio.to_image(fig, format="png", width=900, height=440, scale=1.4)
                img = Image(io.BytesIO(img_bytes), width=avail_w, height=avail_w * (440/900))
                max_h = 3.0*inch
                if img.drawHeight > max_h:
                    ratio = max_h / img.drawHeight
                    img.drawHeight = max_h
                    img.drawWidth  = img.drawWidth * ratio

                insight = _analyze_figure(fig_json)
                block = [
                    Paragraph(label, chart_title_style),
                    img,
                    Spacer(1, 0.04*inch),
                    Paragraph("ANALYST INSIGHT", insight_label_style),
                    Paragraph(insight, insight_style),
                    Spacer(1, 0.18*inch),
                ]
                story.append(KeepTogether(block))
            except Exception as exc:
                story.append(Paragraph(f"{label} — chart could not be rendered ({exc})", insight_style))

    # Note: raw numeric/categorical stat tables and sample-row dumps are
    # intentionally NOT included here — this is a business report, not a
    # data export. Full data remains available via the CSV/Excel export
    # buttons on the Cleaning page for anyone who needs the raw numbers.

    decorator = _make_page_decorator()
    doc.build(story, onFirstPage=decorator, onLaterPages=decorator)
    return buf.getvalue()


def df_to_excel(df: pd.DataFrame) -> bytes:
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="data")
    return out.getvalue()


def figures_to_pdf(figures: list, title: str = "DericBI Charts") -> bytes:
    """
    Render a list of Plotly figure JSON strings to a single branded PDF.
    Two charts per page (kept reasonably sized, not blown up) to keep file
    size sane even with a large gallery.
    """
    import plotly.io as pio
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Image, Spacer, PageBreak

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=0.4*inch, rightMargin=0.4*inch,
        topMargin=0.45*inch, bottomMargin=0.45*inch,
    )
    story = []

    page_w, page_h = landscape(A4)
    avail_w   = page_w - 0.8*inch
    per_chart_h = (page_h - 1.0*inch) / 2 - 0.15*inch  # two charts stacked per page

    for i, fig_json in enumerate(figures):
        fig = pio.from_json(fig_json) if isinstance(fig_json, str) else fig_json
        fig.update_layout(
            margin=dict(l=40, r=20, t=44, b=36),
            paper_bgcolor="white",
            plot_bgcolor="white",
        )
        # Moderate resolution — sharp on screen/print without bloating the PDF.
        img_bytes = pio.to_image(fig, format="png", width=1000, height=560, scale=1.4)
        img = Image(io.BytesIO(img_bytes), width=avail_w, height=avail_w * (560/1000))
        if img.drawHeight > per_chart_h:
            ratio = per_chart_h / img.drawHeight
            img.drawHeight = per_chart_h
            img.drawWidth  = img.drawWidth * ratio
        story.append(img)

        if i % 2 == 0 and i < len(figures) - 1:
            story.append(Spacer(1, 0.2*inch))
        elif i < len(figures) - 1:
            story.append(PageBreak())

    decorator = _make_page_decorator()
    doc.build(story, onFirstPage=decorator, onLaterPages=decorator)
    return buf.getvalue()


# Legacy alias used by pages/cleaning.py and pages/reporting.py
build_exhaustive_report_data = build_report_data
report_data_to_pdf_bytes     = report_to_pdf
dataframe_to_excel_bytes     = df_to_excel
