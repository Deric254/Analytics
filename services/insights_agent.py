"""
DericBI Business Intelligence Engine
=====================================
Generates actionable business insights — not statistics.
Every output answers: "So what? What should the business DO?"

Zero API keys. Zero external dependencies beyond pandas/numpy.
"""

from __future__ import annotations
import re, math
import pandas as pd
import numpy as np
from typing import Optional


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _coerce(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.select_dtypes(include="object").columns:
        c = pd.to_numeric(out[col], errors="coerce")
        if c.notna().mean() >= 0.75:
            out[col] = c
    return out


def _detect_dates(df: pd.DataFrame) -> list[str]:
    found = []
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            found.append(col)
        elif df[col].dtype == object:
            p = pd.to_datetime(df[col], errors="coerce")
            if p.notna().mean() >= 0.6:
                found.append(col)
    return found


def _best_cat(df: pd.DataFrame, query: str = "") -> Optional[str]:
    """Pick the most business-relevant categorical column."""
    cats = df.select_dtypes(exclude="number").columns.tolist()
    if not cats:
        return None
    # prefer one mentioned in query
    q = query.lower()
    for c in cats:
        if c.lower() in q:
            return c
    # prefer low-cardinality meaningful cols (2–50 unique), skip IDs
    good = [c for c in cats
            if 2 <= df[c].nunique() <= 50
            and not any(kw in c.lower() for kw in ["id","uuid","key","code","hash","index","ref"])]
    return good[0] if good else cats[0]


def _best_num(df: pd.DataFrame, query: str = "") -> Optional[str]:
    """Pick the most business-relevant numeric column."""
    nums = df.select_dtypes(include="number").columns.tolist()
    if not nums:
        return None
    q = query.lower()
    for c in nums:
        if c.lower() in q:
            return c
    # prefer revenue/sales/profit/amount/value cols
    priority = ["revenue","sales","profit","amount","value","income","total","price","cost","spend"]
    for kw in priority:
        for c in nums:
            if kw in c.lower():
                return c
    return nums[0]


def _fmt(v) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "N/A"
    if isinstance(v, (float, np.floating)):
        if abs(v) >= 1_000_000: return f"{v/1_000_000:,.2f}M"
        if abs(v) >= 1_000:     return f"{v:,.0f}"
        return f"{v:.2f}"
    if isinstance(v, (int, np.integer)):
        return f"{int(v):,}"
    return str(v)


def _pct(a, b) -> str:
    return f"{100*a/b:.1f}%" if b else "0%"


def _change_pct(new, old) -> str:
    if not old: return "N/A"
    c = (new - old) / abs(old) * 100
    sign = "+" if c >= 0 else ""
    return f"{sign}{c:.1f}%"


# ─── BI Modules ──────────────────────────────────────────────────────────────

def _revenue_performance(df: pd.DataFrame, query: str) -> list[str]:
    num = _best_num(df, query)
    cat = _best_cat(df, query)
    if not num:
        return ["No numeric (revenue/sales/value) column found. Label your columns clearly — e.g. 'Revenue', 'Sales', 'Amount'."]

    s = pd.to_numeric(df[num], errors="coerce").dropna()
    total = s.sum()
    avg   = s.mean()
    med   = s.median()

    lines = [f"**Revenue & Performance — {num}**"]
    lines.append(f"• Total: {_fmt(total)}  |  Average per record: {_fmt(avg)}  |  Median: {_fmt(med)}")

    # Gap between mean and median signals skew
    if avg > med * 1.3:
        lines.append(f"⚠️ Mean ({_fmt(avg)}) is significantly higher than median ({_fmt(med)}) — a small number of high-value transactions are pulling the average up. "
                     "Focus retention efforts on your top customers.")
    elif med > avg * 1.3:
        lines.append(f"⚠️ A few very low-value records are dragging down the average. Review minimum order thresholds or dormant accounts.")

    # 80/20 rule check
    top20_idx = s.nlargest(max(1, len(s)//5)).index
    top20_share = s[top20_idx].sum() / total if total else 0
    lines.append(f"• Top 20% of records generate {_pct(s[top20_idx].sum(), total)} of total {num}.")
    if top20_share >= 0.7:
        lines.append(f"  → 🎯 Pareto alert: your top 20% drives ≥70% of {num}. Protect these accounts — they are your core business.")

    # Best and worst performers by category
    if cat:
        agg = df.groupby(cat, dropna=False)[num].agg(["sum","mean","count"]).dropna()
        agg.columns = ["total","avg","count"]
        agg = agg.sort_values("total", ascending=False)
        top3 = agg.head(3)
        bot3 = agg.tail(3)

        lines.append(f"\n**Top performers by {cat}:**")
        for grp, row in top3.iterrows():
            share = 100 * row["total"] / total if total else 0
            lines.append(f"  🏆 {grp}: {_fmt(row['total'])} total ({share:.1f}% of all {num}), avg {_fmt(row['avg'])} per record")

        lines.append(f"\n**Weakest performers by {cat}:**")
        for grp, row in bot3.iterrows():
            share = 100 * row["total"] / total if total else 0
            lines.append(f"  🔻 {grp}: {_fmt(row['total'])} total ({share:.1f}%), avg {_fmt(row['avg'])} — investigate or cut losses")

        # Concentration risk
        top1_share = 100 * agg["total"].iloc[0] / total if total else 0
        if top1_share >= 40:
            lines.append(f"\n🚨 Concentration risk: '{agg.index[0]}' alone accounts for {top1_share:.0f}% of {num}. "
                         "Heavy dependence on one segment/product/region is a business risk. Diversify.")

    return lines


def _trend_intelligence(df: pd.DataFrame, query: str) -> list[str]:
    num      = _best_num(df, query)
    date_cols = _detect_dates(df)

    if not num:
        return ["No numeric column found for trend analysis."]

    lines = [f"**Trend Intelligence — {num}**"]

    if not date_cols:
        # No date col — use record order
        s = pd.to_numeric(df[num], errors="coerce").dropna().reset_index(drop=True)
        n = len(s)
        if n < 6:
            return lines + ["Not enough records for trend analysis (need at least 6)."]
        q = max(n//4, 1)
        periods = [s.iloc[:q].mean(), s.iloc[q:2*q].mean(), s.iloc[2*q:3*q].mean(), s.iloc[3*q:].mean()]
        labels  = ["Earliest records","Early-mid","Late-mid","Most recent"]
        lines.append("No date column detected — using record order as time proxy.")
        for label, val in zip(labels, periods):
            lines.append(f"  {label}: {_fmt(val)}")
        chg = _change_pct(periods[-1], periods[0])
        direction = "grown" if periods[-1] > periods[0] else "declined"
        lines.append(f"\n📈 Overall: {num} has {direction} {chg} from earliest to most recent records.")
        if periods[-1] < periods[0] * 0.9:
            lines.append("  ⚠️ Declining trend — investigate root causes. Is this seasonal, a lost customer, or a systemic issue?")
        elif periods[-1] > periods[0] * 1.1:
            lines.append("  ✅ Growing trend — identify what's driving this and double down on it.")
        return lines

    dc  = date_cols[0]
    tmp = df.copy()
    tmp[dc] = pd.to_datetime(tmp[dc], errors="coerce")
    tmp = tmp.dropna(subset=[dc, num]).sort_values(dc)
    tmp[num] = pd.to_numeric(tmp[num], errors="coerce")

    date_range_days = (tmp[dc].max() - tmp[dc].min()).days
    lines.append(f"• Period: {tmp[dc].min().date()} → {tmp[dc].max().date()} ({date_range_days} days)")

    # Choose best period grouping
    if date_range_days > 365:
        tmp["period"] = tmp[dc].dt.to_period("Q").astype(str)
        period_label = "quarter"
    elif date_range_days > 60:
        tmp["period"] = tmp[dc].dt.to_period("M").astype(str)
        period_label = "month"
    else:
        tmp["period"] = tmp[dc].dt.to_period("W").astype(str)
        period_label = "week"

    agg = tmp.groupby("period")[num].sum().dropna()
    if len(agg) < 2:
        return lines + ["Not enough time periods to compute a trend (need at least 2)."]

    # First vs last period
    first_val = agg.iloc[0]
    last_val  = agg.iloc[-1]
    chg       = _change_pct(last_val, first_val)
    direction = "▲ grew" if last_val >= first_val else "▼ declined"

    lines.append(f"• {num} {direction} {chg} from first {period_label} to last {period_label}")
    lines.append(f"  First {period_label} ({agg.index[0]}): {_fmt(first_val)}")
    lines.append(f"  Last  {period_label} ({agg.index[-1]}): {_fmt(last_val)}")

    # Best and worst period
    best_p  = agg.idxmax()
    worst_p = agg.idxmin()
    lines.append(f"\n• Best {period_label}: {best_p} → {_fmt(agg[best_p])}")
    lines.append(f"• Worst {period_label}: {worst_p} → {_fmt(agg[worst_p])}")

    # Volatility
    cv = agg.std() / agg.mean() if agg.mean() else 0
    if cv > 0.3:
        lines.append(f"\n⚠️ High volatility (CV={cv:.2f}) — {num} fluctuates significantly period to period. "
                     "Inconsistent performance may indicate seasonal effects, irregular ordering, or operational issues.")
    else:
        lines.append(f"\n✅ Relatively stable performance (CV={cv:.2f}) across periods.")

    # Last 2 periods momentum
    if len(agg) >= 3:
        prev    = agg.iloc[-2]
        current = agg.iloc[-1]
        mom     = _change_pct(current, prev)
        if current < prev * 0.85:
            lines.append(f"🚨 Recent momentum: last {period_label} dropped {mom} vs prior. Immediate attention needed.")
        elif current > prev * 1.15:
            lines.append(f"🚀 Recent momentum: last {period_label} grew {mom} vs prior. What drove this? Replicate it.")

    return lines


def _customer_segment_analysis(df: pd.DataFrame, query: str) -> list[str]:
    num = _best_num(df, query)
    cat = _best_cat(df, query)

    if not cat or not num:
        return ["Need at least one categorical column (e.g. Customer, Region, Product, Segment) and one numeric column (e.g. Revenue)."]

    lines = [f"**Segment Analysis — {num} by {cat}**"]
    agg = df.groupby(cat, dropna=False)[num].agg(["sum","mean","count"]).dropna()
    agg.columns = ["total","avg","count"]
    agg = agg.sort_values("total", ascending=False)
    grand_total = agg["total"].sum()

    # Segment summary
    lines.append(f"• {agg.shape[0]} segments in '{cat}'")
    lines.append(f"• Grand total {num}: {_fmt(grand_total)}")

    lines.append(f"\n**Segment breakdown:**")
    cum = 0
    for i, (grp, row) in enumerate(agg.iterrows()):
        share = 100 * row["total"] / grand_total if grand_total else 0
        cum  += share
        flag  = " ← 80% threshold crossed" if cum >= 80 and (cum - share) < 80 else ""
        lines.append(
            f"  {i+1}. {grp}: {_fmt(row['total'])} ({share:.1f}%)  "
            f"avg={_fmt(row['avg'])}  n={int(row['count'])}{flag}"
        )

    # Concentration
    if len(agg) >= 3:
        top3_share = 100 * agg["total"].iloc[:3].sum() / grand_total if grand_total else 0
        lines.append(f"\n• Top 3 segments = {top3_share:.0f}% of all {num}")
        if top3_share >= 80:
            lines.append(f"  🎯 High concentration — 3 segments drive 80%+ of value. These are your priority. "
                         "But also a risk if any one drops off.")

    # Underperforming segments
    avg_val = agg["avg"].mean()
    underperformers = agg[agg["avg"] < avg_val * 0.5]
    if not underperformers.empty:
        lines.append(f"\n⚠️ Underperforming segments (avg {num} < 50% of overall average {_fmt(avg_val)}):")
        for grp, row in underperformers.head(3).iterrows():
            lines.append(f"  • {grp}: avg {_fmt(row['avg'])} per record — review pricing, activity, or cut")

    return lines


def _profitability_analysis(df: pd.DataFrame, query: str) -> list[str]:
    """Find revenue, cost, profit relationships."""
    nums = df.select_dtypes(include="number").columns.tolist()
    cat  = _best_cat(df, query)

    # Try to detect revenue and cost columns
    rev_kw  = ["revenue","sales","income","turnover","amount","price","value","total"]
    cost_kw = ["cost","expense","spend","cogs","purchase","payment","outgoing"]

    rev_col  = next((c for kw in rev_kw  for c in nums if kw in c.lower()), None)
    cost_col = next((c for kw in cost_kw for c in nums if kw in c.lower() and c != rev_col), None)

    if not rev_col:
        return _revenue_performance(df, query)

    lines = [f"**Profitability Analysis**"]
    rev_s = pd.to_numeric(df[rev_col], errors="coerce").dropna()
    lines.append(f"• Revenue column: {rev_col}  →  Total: {_fmt(rev_s.sum())}, Avg: {_fmt(rev_s.mean())}")

    if cost_col:
        cost_s = pd.to_numeric(df[cost_col], errors="coerce")
        df2 = df.copy()
        df2["__profit__"] = pd.to_numeric(df2[rev_col], errors="coerce") - pd.to_numeric(df2[cost_col], errors="coerce")
        profit_s = df2["__profit__"].dropna()
        total_rev  = rev_s.sum()
        total_cost = cost_s.dropna().sum()
        total_profit = profit_s.sum()
        margin = 100 * total_profit / total_rev if total_rev else 0

        lines.append(f"• Cost column: {cost_col}  →  Total: {_fmt(total_cost)}")
        lines.append(f"• Net profit: {_fmt(total_profit)}  |  Margin: {margin:.1f}%")

        if margin < 10:
            lines.append(f"  🚨 Margin of {margin:.1f}% is very thin. Any cost increase or revenue dip could result in a loss. "
                         "Identify the biggest cost drivers immediately.")
        elif margin < 25:
            lines.append(f"  ⚠️ Margin of {margin:.1f}% is acceptable but has room for improvement. "
                         "Review high-cost segments and consider price optimisation.")
        else:
            lines.append(f"  ✅ Margin of {margin:.1f}% is healthy. Focus on scaling volume.")

        # Loss-making records
        losses = df2[df2["__profit__"] < 0]
        if not losses.empty:
            loss_total = abs(losses["__profit__"].sum())
            lines.append(f"\n⚠️ {len(losses):,} records are loss-making (negative profit) totalling {_fmt(loss_total)} in losses.")
            if cat and cat in df2.columns:
                loss_by_cat = losses.groupby(cat, dropna=False)["__profit__"].sum().sort_values().head(3)
                lines.append(f"  Biggest loss-makers by {cat}:")
                for grp, val in loss_by_cat.items():
                    lines.append(f"    {grp}: {_fmt(val)}")

        # Best margin segment
        if cat and cat in df.columns:
            grp = df2.groupby(cat, dropna=False).agg(
                rev   =(rev_col,  "sum"),
                profit=("__profit__", "sum"),
            ).dropna()
            grp["margin"] = 100 * grp["profit"] / grp["rev"].replace(0, np.nan)
            grp = grp.sort_values("margin", ascending=False).dropna(subset=["margin"])
            if not grp.empty:
                lines.append(f"\n**Margin by {cat}:**")
                for g, r in grp.iterrows():
                    flag = " 🏆" if r["margin"] == grp["margin"].max() else (" 🚨" if r["margin"] < 0 else "")
                    lines.append(f"  {g}: {r['margin']:.1f}% margin  (revenue {_fmt(r['rev'])}, profit {_fmt(r['profit'])}){flag}")
    else:
        lines.append(f"\n💡 No cost column detected. To get profitability analysis, add a column named 'Cost', 'Expense', or 'COGS'.")

    return lines


def _growth_opportunity(df: pd.DataFrame, query: str) -> list[str]:
    """Identify growth opportunities and underserved segments."""
    num = _best_num(df, query)
    cat = _best_cat(df, query)
    date_cols = _detect_dates(df)

    lines = ["**Growth Opportunities**"]

    if not num or not cat:
        return lines + ["Need at least one numeric column and one categorical column to identify growth opportunities."]

    agg = df.groupby(cat, dropna=False)[num].agg(["sum","mean","count"]).dropna()
    agg.columns = ["total","avg","count"]
    grand_total = agg["total"].sum()
    overall_avg = agg["avg"].mean()

    # High volume, low average = undermonetised
    high_count = agg[agg["count"] > agg["count"].quantile(0.75)]
    if not high_count.empty:
        low_avg_high_vol = high_count[high_count["avg"] < overall_avg * 0.8]
        if not low_avg_high_vol.empty:
            lines.append(f"\n🎯 High-volume, undermonetised segments (many transactions but low average {num}):")
            for grp, row in low_avg_high_vol.head(3).iterrows():
                upside = (overall_avg - row["avg"]) * row["count"]
                lines.append(
                    f"  • {grp}: {int(row['count']):,} records at avg {_fmt(row['avg'])} "
                    f"— raising to average would add {_fmt(upside)} revenue"
                )
            lines.append("  → These segments buy frequently. A price increase or upsell could significantly lift revenue.")

    # Low volume, high average = scalable premium segments
    low_count = agg[agg["count"] < agg["count"].quantile(0.25)]
    if not low_count.empty:
        high_avg_low_vol = low_count[low_count["avg"] > overall_avg * 1.2]
        if not high_avg_low_vol.empty:
            lines.append(f"\n💎 High-value but low-frequency segments (premium opportunity):")
            for grp, row in high_avg_low_vol.head(3).iterrows():
                lines.append(
                    f"  • {grp}: avg {_fmt(row['avg'])} per record but only {int(row['count']):,} records "
                    f"— invest in growing this segment"
                )
            lines.append("  → These segments pay well. Find more like them or increase their purchase frequency.")

    # Zero or missing segments (gaps)
    all_cats = df[cat].dropna().astype(str).unique()
    if len(all_cats) <= 20:
        lines.append(f"\n📊 All {len(all_cats)} segments are active in {cat}.")

    # Trend by segment if date available
    if date_cols:
        dc = date_cols[0]
        tmp = df.copy()
        tmp[dc] = pd.to_datetime(tmp[dc], errors="coerce")
        tmp = tmp.dropna(subset=[dc]).sort_values(dc)
        half = tmp[dc].quantile(0.5)
        first_half = tmp[tmp[dc] <= half].groupby(cat, dropna=False)[num].sum()
        second_half = tmp[tmp[dc] > half].groupby(cat, dropna=False)[num].sum()
        both = pd.DataFrame({"h1": first_half, "h2": second_half}).dropna()
        both["growth"] = (both["h2"] - both["h1"]) / both["h1"].abs().replace(0, np.nan) * 100
        both = both.dropna(subset=["growth"])
        if not both.empty:
            fastest = both["growth"].nlargest(3)
            slowest = both["growth"].nsmallest(3)
            lines.append(f"\n**Fastest-growing segments (first half vs second half of period):**")
            for grp, g in fastest.items():
                lines.append(f"  📈 {grp}: {'+' if g>=0 else ''}{g:.1f}%")
            lines.append(f"\n**Fastest-declining segments:**")
            for grp, g in slowest.items():
                lines.append(f"  📉 {grp}: {g:.1f}%  — investigate cause")

    return lines


def _risk_flags(df: pd.DataFrame, query: str) -> list[str]:
    """Identify business risks in the data."""
    num  = _best_num(df, query)
    cat  = _best_cat(df, query)
    date_cols = _detect_dates(df)

    lines = ["**Business Risk Flags**"]

    # Data quality risks
    missing = int(df.isna().sum().sum())
    total_cells = df.shape[0] * df.shape[1]
    dups = int(df.duplicated().sum())
    if missing > 0:
        miss_pct = 100*missing/total_cells
        lines.append(f"⚠️ Data quality: {missing:,} missing values ({miss_pct:.1f}%). "
                     "Decisions based on incomplete data carry risk.")
        worst = df.isna().sum().sort_values(ascending=False).head(3)
        for col, cnt in worst.items():
            if cnt > 0:
                lines.append(f"   Column '{col}': {cnt:,} missing ({_pct(cnt, df.shape[0])})")
    if dups > 0:
        lines.append(f"⚠️ {dups:,} duplicate records — could inflate totals or KPIs. Clean on the Cleaning page.")

    # Revenue concentration risk
    if num and cat:
        agg = df.groupby(cat, dropna=False)[num].sum().sort_values(ascending=False).dropna()
        grand = agg.sum()
        if grand > 0 and len(agg) >= 2:
            top1_share = agg.iloc[0] / grand * 100
            top3_share = agg.iloc[:3].sum() / grand * 100
            if top1_share >= 40:
                lines.append(f"🚨 Concentration risk: '{agg.index[0]}' accounts for {top1_share:.0f}% of {num}. "
                             "Losing this single account/segment could be catastrophic.")
            if top3_share >= 80 and len(agg) > 3:
                lines.append(f"🚨 Top 3 segments = {top3_share:.0f}% of {num}. Business is fragile if any one declines.")

    # Outlier / spike risk
    if num:
        s = pd.to_numeric(df[num], errors="coerce").dropna()
        if len(s) >= 4:
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            outliers = s[(s < q1 - 3*iqr) | (s > q3 + 3*iqr)]
            if not outliers.empty:
                lines.append(f"⚠️ {len(outliers):,} extreme value(s) in '{num}' — "
                             f"range {_fmt(outliers.min())} to {_fmt(outliers.max())}. "
                             "Verify these are real and not data entry errors.")

    # Trend reversal risk
    if num and date_cols:
        dc = date_cols[0]
        tmp = df[[dc, num]].copy()
        tmp[dc] = pd.to_datetime(tmp[dc], errors="coerce")
        tmp = tmp.dropna().sort_values(dc)
        tmp[num] = pd.to_numeric(tmp[num], errors="coerce")
        if len(tmp) >= 6:
            n = max(len(tmp)//4, 1)
            peak = tmp[num].rolling(n).mean().max()
            latest = tmp[num].iloc[-n:].mean()
            if pd.notna(peak) and peak > 0 and latest < peak * 0.7:
                lines.append(f"📉 {num} is currently {_pct(latest, peak)} of its peak value. "
                             "This is a significant decline from historical high — investigate.")

    # Negative values in revenue
    if num:
        s = pd.to_numeric(df[num], errors="coerce").dropna()
        neg = s[s < 0]
        if not neg.empty:
            lines.append(f"🔴 {len(neg):,} negative values in '{num}' totalling {_fmt(neg.sum())}. "
                         "These could be refunds, chargebacks, or data errors — investigate each one.")

    if len(lines) == 1:
        lines.append("✅ No major business risks detected in this dataset.")

    return lines


def _pricing_analysis(df: pd.DataFrame, query: str) -> list[str]:
    """Analyse pricing effectiveness."""
    nums = df.select_dtypes(include="number").columns.tolist()
    cat  = _best_cat(df, query)

    price_kw = ["price","rate","fee","charge","tariff","unit_price","selling"]
    qty_kw   = ["qty","quantity","units","volume","count","pieces","items"]
    rev_kw   = ["revenue","sales","amount","total","value","income"]

    price_col = next((c for kw in price_kw for c in nums if kw in c.lower()), None)
    qty_col   = next((c for kw in qty_kw   for c in nums if kw in c.lower()), None)
    rev_col   = next((c for kw in rev_kw   for c in nums if kw in c.lower()), None)

    lines = ["**Pricing Analysis**"]

    if not price_col and not (qty_col and rev_col):
        lines.append("💡 For pricing analysis, include columns named 'Price', 'Rate', or 'Unit_Price'.")
        lines.append("   Alternatively, have both 'Quantity' and 'Revenue' columns to compute implied price.")
        return lines

    # Compute implied price if no direct price col
    if not price_col and qty_col and rev_col:
        df2 = df.copy()
        df2["__implied_price__"] = pd.to_numeric(df2[rev_col], errors="coerce") / pd.to_numeric(df2[qty_col], errors="coerce").replace(0, np.nan)
        price_col = "__implied_price__"
        lines.append(f"• Implied price = {rev_col} ÷ {qty_col}")

    p = pd.to_numeric(df[price_col] if price_col in df.columns else df["__implied_price__"] if "__implied_price__" in df.columns else pd.Series(dtype=float), errors="coerce").dropna()

    if p.empty:
        return lines + ["Could not compute price values."]

    lines.append(f"• Price range: {_fmt(p.min())} – {_fmt(p.max())}")
    lines.append(f"• Average price: {_fmt(p.mean())}  |  Median: {_fmt(p.median())}")
    cv = p.std() / p.mean() if p.mean() else 0
    if cv > 0.3:
        lines.append(f"⚠️ High price variation (CV={cv:.2f}) — are different customers being charged different rates? "
                     "Review pricing consistency.")

    if cat and cat in df.columns:
        agg = df.groupby(cat, dropna=False).apply(
            lambda x: pd.to_numeric(x[price_col] if price_col in df.columns else None, errors="coerce").mean()
            if price_col in df.columns else np.nan
        ).dropna().sort_values(ascending=False)
        if not agg.empty:
            lines.append(f"\n**Average price by {cat}:**")
            for grp, val in agg.items():
                flag = " ← highest" if val == agg.max() else (" ← lowest" if val == agg.min() else "")
                lines.append(f"  {grp}: {_fmt(val)}{flag}")
            price_gap = (agg.max() - agg.min()) / agg.mean() * 100 if agg.mean() else 0
            if price_gap > 50:
                lines.append(f"\n⚠️ {price_gap:.0f}% price gap between highest and lowest {cat}. "
                             "Is this intentional (tiered pricing) or an inconsistency to fix?")

    return lines


def _action_summary(df: pd.DataFrame, query: str) -> list[str]:
    """Top business actions — always produces meaningful output."""
    num       = _best_num(df, query)
    cat       = _best_cat(df, query)
    date_cols = _detect_dates(df)
    nums      = df.select_dtypes(include="number").columns.tolist()

    lines   = ["**Top Business Actions — What To Do Now**"]
    actions = []
    idx     = 1

    # 1. Missing data — always check first
    total_missing = int(df.isna().sum().sum())
    if total_missing > 0:
        worst_col = df.isna().sum().idxmax()
        worst_cnt = int(df[worst_col].isna().sum())
        pct = 100 * worst_cnt / max(len(df), 1)
        actions.append(
            f"{idx}. 🧹 **Fix missing data** — {total_missing:,} missing values across your dataset. "
            f"Worst: '{worst_col}' has {worst_cnt:,} gaps ({pct:.1f}%). "
            "Go to Cleaning page → choose Fill or Drop strategy. Decisions made on incomplete data are unreliable."
        )
        idx += 1

    # 2. Duplicates
    dups = int(df.duplicated().sum())
    if dups > 0:
        actions.append(
            f"{idx}. 🧹 **Remove {dups:,} duplicate rows** — they inflate your totals and KPIs. "
            "Go to Cleaning → Remove exact duplicates."
        )
        idx += 1

    # 3. Concentration risk or top performer
    if num and cat:
        agg = df.groupby(cat, dropna=False)[num].sum().sort_values(ascending=False).dropna()
        grand = agg.sum()
        if grand > 0 and len(agg) >= 2:
            top1_share = agg.iloc[0] / grand * 100
            if top1_share >= 30:
                actions.append(
                    f"{idx}. 🎯 **Protect '{agg.index[0]}'** — drives {top1_share:.0f}% of {num}. "
                    "This is your most critical account/segment. Any disruption here is a major business risk. "
                    "Prioritise relationship management and service quality."
                )
            else:
                # Healthy spread — recommend doubling down on top
                actions.append(
                    f"{idx}. 🏆 **Double down on '{agg.index[0]}'** — your top {cat} segment "
                    f"({top1_share:.0f}% of {num}). Allocate more resources and sales effort here. "
                    f"Gap to #2 ('{agg.index[1]}') is {_fmt(agg.iloc[0] - agg.iloc[1])}."
                )
            idx += 1

    # 4. Trend action
    if num and date_cols:
        dc  = date_cols[0]
        tmp = df[[dc, num]].copy()
        tmp[dc] = pd.to_datetime(tmp[dc], errors="coerce")
        tmp[num] = pd.to_numeric(tmp[num], errors="coerce")
        tmp = tmp.dropna().sort_values(dc)
        if len(tmp) >= 6:
            n = max(len(tmp) // 4, 1)
            first = tmp[num].iloc[:n].mean()
            last  = tmp[num].iloc[-n:].mean()
            if pd.notna(first) and pd.notna(last) and first > 0:
                chg = (last - first) / abs(first) * 100
                if chg < -15:
                    actions.append(
                        f"{idx}. 📉 **Urgent: {num} is down {abs(chg):.1f}%** from first quarter to latest. "
                        "Pull a period comparison in Visualization to find exactly when it started declining. "
                        "Cross-reference with any operational changes in that period."
                    )
                elif chg > 15:
                    actions.append(
                        f"{idx}. 🚀 **Capitalise on growth: {num} is up {chg:.1f}%**. "
                        "Identify the specific driver — product mix, new segment, pricing change? "
                        "Whatever is working, do more of it before competitors catch up."
                    )
                else:
                    actions.append(
                        f"{idx}. 📊 **{num} is stable ({chg:+.1f}% trend)**. "
                        "Stability is safe but not growth. Run a segment breakdown to find which sub-groups "
                        "are growing (exploit them) and which are declining (fix or exit)."
                    )
                idx += 1

    # 5. Underperforming segments
    if num and cat:
        agg = df.groupby(cat, dropna=False)[num].agg(["mean", "count"]).dropna()
        overall_avg = agg["mean"].mean()
        under = agg[agg["mean"] < overall_avg * 0.6].sort_values("mean")
        if not under.empty:
            names = ", ".join(f"'{g}'" for g in under.index[:3])
            actions.append(
                f"{idx}. 🔻 **Review weak segments: {names}** — performing at less than 60% of average {num}. "
                "For each: (a) Is volume growing? If yes, invest. (b) Is it shrinking? Cut losses or restructure pricing."
            )
            idx += 1

    # 6. Negative values
    if num:
        s = pd.to_numeric(df[num], errors="coerce").dropna()
        neg = s[s < 0]
        if not neg.empty:
            actions.append(
                f"{idx}. 🔴 **Investigate {len(neg):,} negative {num} values** (total: {_fmt(neg.sum())}). "
                "Are these refunds, chargebacks, adjustments, or data entry errors? "
                "Each one is either a real loss or a data quality problem — both need attention."
            )
            idx += 1

    # 7. Outlier / extreme values
    if num:
        s = pd.to_numeric(df[num], errors="coerce").dropna()
        if len(s) >= 4:
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                extremes = s[s > q3 + 3 * iqr]
                if not extremes.empty:
                    actions.append(
                        f"{idx}. ⚠️ **Verify {len(extremes):,} extreme {num} value(s)** "
                        f"(up to {_fmt(extremes.max())}). "
                        "Unusually large values could be legitimate windfalls or data entry errors. "
                        "Confirm each one before including in forecasts."
                    )
                    idx += 1

    # 8. Profitability if both rev and cost found
    nums_all = df.select_dtypes(include="number").columns.tolist()
    rev_col  = next((c for kw in ["revenue","sales","income","amount","total"] for c in nums_all if kw in c.lower()), None)
    cost_col = next((c for kw in ["cost","expense","cogs","spend"] for c in nums_all if kw in c.lower() and c != rev_col), None)
    if rev_col and cost_col:
        rev_total  = pd.to_numeric(df[rev_col],  errors="coerce").dropna().sum()
        cost_total = pd.to_numeric(df[cost_col], errors="coerce").dropna().sum()
        if rev_total > 0:
            margin = 100 * (rev_total - cost_total) / rev_total
            if margin < 15:
                actions.append(
                    f"{idx}. 💰 **Margin alert: {margin:.1f}%** ({rev_col} vs {cost_col}). "
                    "Below 15% leaves little buffer. Review your biggest cost line items and consider "
                    "a price increase or cost renegotiation."
                )
                idx += 1
            elif margin > 40:
                actions.append(
                    f"{idx}. 💡 **Strong margin: {margin:.1f}%** — you have pricing power. "
                    "Consider whether reinvesting some margin into growth (marketing, capacity) "
                    "could compound returns faster than protecting the current margin."
                )
                idx += 1

    # Always end with a BI recommendation
    actions.append(
        f"{idx}. 📊 **Build a regular review cadence** — load updated data monthly, "
        "run the Trend and Segment analysis, and compare vs prior period. "
        "Consistent monitoring catches problems early and confirms what is working."
    )

    lines += actions
    return lines


# ─── Keyword Router ───────────────────────────────────────────────────────────

_ROUTES = [
    (r"revenue|sales|income|performance|total|amount|value|earning",    "revenue"),
    (r"trend|over time|growth|decline|month|quarter|year|period|time",  "trend"),
    (r"profit|margin|cost|expense|cogs|loss|net",                       "profit"),
    (r"segment|region|product|category|group|by|breakdown|split|who",   "segment"),
    (r"grow|opportunit|potential|scale|expand|upsell|untap|gap",        "growth"),
    (r"risk|danger|warning|alert|concentrat|vulnerab|fragile",          "risk"),
    (r"price|pricing|rate|fee|charge|cheap|expensive|discount",         "pricing"),
    (r"action|recommend|what should|next step|do now|help|advice|suggest|tell me what", "actions"),
]


def _route(query: str) -> str:
    q = query.lower()
    for pattern, label in _ROUTES:
        if re.search(pattern, q):
            return label
    return "actions"   # default: give actions


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_insight(query: str, df: "pd.DataFrame | None" = None) -> str:
    if not query:
        return "Ask a business question — e.g. 'what are my top revenue segments?' or 'what should I do now?'"
    if df is None or df.empty:
        return "No dataset loaded. Upload data on the Ingestion page first."

    df = _coerce(df)
    route = _route(query)

    dispatch = {
        "revenue":  lambda: _revenue_performance(df, query),
        "trend":    lambda: _trend_intelligence(df, query),
        "profit":   lambda: _profitability_analysis(df, query),
        "segment":  lambda: _customer_segment_analysis(df, query),
        "growth":   lambda: _growth_opportunity(df, query),
        "risk":     lambda: _risk_flags(df, query),
        "pricing":  lambda: _pricing_analysis(df, query),
        "actions":  lambda: _action_summary(df, query),
    }

    lines = dispatch.get(route, dispatch["actions"])()
    return "\n".join(lines)
