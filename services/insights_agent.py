"""
DericBI Universal Intelligence Engine
=======================================
Works on ANY dataset — sales, medical, academic, weather, inventory,
sports, logistics, or anything else.

Zero hardcoded column names. Zero hardcoded domain language.
Auto-discovers structure, picks the right columns, adapts terminology.
"""

from __future__ import annotations
import re, math
import pandas as pd
import numpy as np


# ═══════════════════════════════════════════════════════════════════════════════
#  DATASET PROFILER — understands what kind of data this is
# ═══════════════════════════════════════════════════════════════════════════════

class DataProfile:
    """Auto-discovers the structure and domain of any DataFrame."""

    def __init__(self, df: pd.DataFrame, query: str = ""):
        self.df    = df
        self.query = query.lower()
        self.rows, self.cols_count = df.shape

        # Column classifications
        self.numeric_cols     = df.select_dtypes(include="number").columns.tolist()
        self.all_cols         = df.columns.tolist()
        self.date_cols        = self._find_dates()
        self.cat_cols         = self._find_cats()

        # Semantic roles — what each column likely represents
        self.value_col   = self._pick_value_col()    # primary numeric KPI
        self.cost_col    = self._pick_col_by_role("cost")
        self.qty_col     = self._pick_col_by_role("qty")
        self.price_col   = self._pick_col_by_role("price")
        self.group_cols  = self._pick_group_cols()   # best categorical groupers
        self.date_col    = self.date_cols[0] if self.date_cols else None

        # Domain detection
        self.domain = self._detect_domain()

    # ── Column finders ────────────────────────────────────────────────────────

    def _find_dates(self):
        found = []
        for col in self.all_cols:
            if pd.api.types.is_datetime64_any_dtype(self.df[col]):
                found.append(col)
            elif self.df[col].dtype == object:
                p = pd.to_datetime(self.df[col], errors="coerce")
                if p.notna().mean() >= 0.6:
                    found.append(col)
        return found

    def _find_cats(self):
        date_cols = self._find_dates()
        cats = []
        for col in self.all_cols:
            if col in self.numeric_cols or col in date_cols:
                continue
            n_unique = self.df[col].nunique()
            n_rows   = len(self.df)
            # Skip if too many unique values relative to rows (likely an ID/text field)
            if n_unique >= 1 and n_unique / n_rows < 0.5 and n_unique <= 100:
                cats.append(col)
        return cats

    def _pick_col_by_role(self, role: str) -> str | None:
        """Match a column to a semantic role using keyword families."""
        KW = {
            "value":  ["revenue","sales","income","amount","value","total","receipts",
                       "gross","score","marks","rating","price","bill","fee","charge",
                       "spend","count","qty","quantity","stock","units","volume","output",
                       "production","yield","weight","length","height","temperature",
                       "distance","duration","salary","wage","cost","expense"],
            "cost":   ["cost","expense","cogs","overhead","expenditure","spend",
                       "payment","outgoing","wages","salary","outflow"],
            "qty":    ["qty","quantity","units","volume","count","pieces","items",
                       "sold","orders","number","total_count","days","hours"],
            "price":  ["price","rate","fee","charge","tariff","unit_price",
                       "selling_price","fare","rate_per"],
        }
        keywords = KW.get(role, [])
        # 1. Mentioned in user query
        for col in self.numeric_cols:
            if col.lower() in self.query:
                return col
        # 2. Keyword match
        for kw in keywords:
            for col in self.numeric_cols:
                if kw in col.lower():
                    return col
        return None

    def _pick_value_col(self) -> str | None:
        """Pick the single most important numeric column for this dataset."""
        if not self.numeric_cols:
            return None
        # Mentioned in query
        for col in self.numeric_cols:
            if col.lower() in self.query:
                return col
        # Skip pure ID columns (monotonically increasing integers)
        candidates = []
        for col in self.numeric_cols:
            s = pd.to_numeric(self.df[col], errors="coerce").dropna()
            if len(s) < 2:
                continue
            # Skip if it looks like an auto-increment ID
            if s.is_monotonic_increasing and s.nunique() == len(s):
                continue
            candidates.append(col)

        if not candidates:
            return self.numeric_cols[0]

        # Pick highest variance (most interesting spread)
        return max(candidates, key=lambda c: pd.to_numeric(self.df[c], errors="coerce").std() or 0)

    def _pick_group_cols(self, max_n: int = 3) -> list[str]:
        """Best categorical columns for grouping — skip IDs, pick meaningful ones."""
        q = self.query
        mentioned = [c for c in self.cat_cols if c.lower() in q]
        rest = [c for c in self.cat_cols if c not in mentioned]
        # Sort by cardinality: prefer 2–20 unique values (most meaningful segments)
        def score(c):
            n = self.df[c].nunique()
            return abs(n - 8)   # closer to 8 unique values = better grouper
        rest.sort(key=score)
        return (mentioned + rest)[:max_n]

    # ── Domain detection ──────────────────────────────────────────────────────

    def _detect_domain(self) -> str:
        col_text = " ".join(self.all_cols).lower()
        checks = [
            ("medical",    r"patient|ward|diagnosis|symptom|admission|discharge|doctor|nurse|hospital|medicine|dose|blood|icu"),
            ("academic",   r"student|grade|score|marks|subject|class|teacher|exam|course|gpa|attendance|school"),
            ("weather",    r"temperature|rainfall|humidity|wind|pressure|forecast|climate|precipitation|season"),
            ("inventory",  r"stock|reorder|warehouse|sku|item|shelf|batch|expiry|supplier|bin|qty|quantity"),
            ("logistics",  r"shipment|delivery|route|vehicle|driver|cargo|tracking|dispatch|freight|trip"),
            ("hr",         r"employee|staff|department|salary|leave|hire|payroll|headcount|performance"),
            ("financial",  r"revenue|sales|profit|cost|expense|margin|budget|forecast|invoice|payment"),
            ("sports",     r"match|team|player|goal|score|win|loss|league|tournament|season|points"),
        ]
        for domain, pattern in checks:
            if re.search(pattern, col_text):
                return domain
        return "general"

    # ── Terminology adapter ───────────────────────────────────────────────────

    def term(self, role: str) -> str:
        """Return domain-appropriate terminology for a role."""
        MAP = {
            "value": {
                "medical":   "amount",
                "academic":  "score",
                "weather":   "measurement",
                "inventory": "quantity",
                "hr":        "value",
                "financial": "revenue",
                "sports":    "score",
                "general":   "value",
            },
            "top_group": {
                "medical":   "ward/diagnosis",
                "academic":  "subject/class",
                "weather":   "region",
                "inventory": "item/warehouse",
                "hr":        "department",
                "financial": "segment",
                "sports":    "team",
                "general":   "group",
            },
            "trend": {
                "medical":   "case volume",
                "academic":  "performance",
                "weather":   "conditions",
                "inventory": "stock movement",
                "hr":        "headcount / activity",
                "financial": "revenue",
                "sports":    "performance",
                "general":   "trend",
            },
        }
        return MAP.get(role, {}).get(self.domain, role)


# ═══════════════════════════════════════════════════════════════════════════════
#  FORMATTING
# ═══════════════════════════════════════════════════════════════════════════════

def _coerce(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.select_dtypes(include="object").columns:
        c = pd.to_numeric(out[col], errors="coerce")
        if c.notna().mean() >= 0.75:
            out[col] = c
    return out


def _fmt(v) -> str:
    """Always 2 decimal places, comma-separated thousands. Clean and consistent."""
    try:
        f = float(v)
        if math.isnan(f): return "N/A"
        return f"{f:,.2f}"
    except (TypeError, ValueError):
        return str(v)


def _fmt_compact(v) -> str:
    """Compact K/M/B format for chart labels and tight spaces — still 2 decimals."""
    try:
        f = float(v)
        if math.isnan(f): return "N/A"
        if abs(f) >= 1_000_000_000: return f"{f/1_000_000_000:,.2f}B"
        if abs(f) >= 1_000_000:     return f"{f/1_000_000:,.2f}M"
        if abs(f) >= 1_000:         return f"{f/1_000:,.2f}K"
        return f"{f:,.2f}"
    except (TypeError, ValueError):
        return str(v)


def _pct(a, b) -> str:
    return f"{100*a/b:.1f}%" if b else "0%"


def _chg(new, old) -> str:
    if not old: return "N/A"
    c = (new - old) / abs(old) * 100
    return f"{'+' if c>=0 else ''}{c:.1f}%"


def _series(df, col):
    return pd.to_numeric(df[col], errors="coerce").dropna()


# ═══════════════════════════════════════════════════════════════════════════════
#  BI MODULES — each uses DataProfile, fully domain-agnostic
# ═══════════════════════════════════════════════════════════════════════════════

def _overview(p: DataProfile) -> list[str]:
    df  = p.df
    num = p.value_col
    cat = p.group_cols[0] if p.group_cols else None

    lines = [f"**Dataset Overview ({p.domain.title()} data)**"]
    lines.append(f"• {p.rows:,} records × {p.cols_count} columns")
    lines.append(f"• Numeric columns: {len(p.numeric_cols)}  |  "
                 f"Categorical: {len(p.cat_cols)}  |  "
                 f"Date: {len(p.date_cols)}")

    missing = int(df.isna().sum().sum())
    dups    = int(df.duplicated().sum())
    total   = p.rows * p.cols_count
    lines.append(f"• Completeness: {_pct(total-missing, total)}  |  "
                 f"Duplicates: {dups:,}")

    if num:
        s = _series(df, num)
        lines.append(f"\n**Key metric: {num}**")
        lines.append(f"• Total: {_fmt(s.sum())}  |  Avg: {_fmt(s.mean())}  |  "
                     f"Median: {_fmt(s.median())}  |  Std: {_fmt(s.std())}")
        lines.append(f"• Range: {_fmt(s.min())} → {_fmt(s.max())}")

    if cat and num:
        agg = df.groupby(cat, dropna=False)[num].sum().sort_values(ascending=False).dropna()
        grand = agg.sum()
        lines.append(f"\n**Top values by {cat}:**")
        for grp, val in agg.head(5).items():
            lines.append(f"  • {grp}: {_fmt(val)} ({_pct(val, grand)})")

    return lines


def _performance_analysis(p: DataProfile) -> list[str]:
    df  = p.df
    num = p.value_col
    cat = p.group_cols[0] if p.group_cols else None

    if not num:
        return ["No numeric column found to analyse performance. "
                "Please upload data with at least one numeric column."]

    s     = _series(df, num)
    total = s.sum()
    lines = [f"**Performance Analysis — {num}**"]
    lines.append(f"• Total: {_fmt(total)}  |  Avg: {_fmt(s.mean())}  |  Median: {_fmt(s.median())}  |  Std dev: {_fmt(s.std())}")

    # Spread interpretation
    cv = s.std() / s.mean() if s.mean() else 0
    if cv > 0.5:
        lines.append(f"• High variability (CV={cv:.2f}) — values spread widely. "
                     "Some records far outperform others.")
    elif cv < 0.1:
        lines.append(f"• Very consistent values (CV={cv:.2f}) — little variation across records.")

    # Mean vs median skew
    if s.mean() > s.median() * 1.3:
        lines.append(f"• Mean ({_fmt(s.mean())}) >> Median ({_fmt(s.median())}) — "
                     "a small number of high values are pulling the average up. "
                     "Most records cluster lower.")
    elif s.median() > s.mean() * 1.3:
        lines.append(f"• Median ({_fmt(s.median())}) >> Mean ({_fmt(s.mean())}) — "
                     "a few very low values drag the average down.")

    # Top 20% contribution — only meaningful when all values share the same
    # sign as the total; with mixed positive/negative values a "share of
    # total" figure can exceed 100% or go negative, which is accurate math
    # but reads as broken. Skip it in that case rather than show a
    # nonsensical percentage.
    top20 = s.nlargest(max(1, len(s)//5))
    all_same_sign = (s >= 0).all() or (s <= 0).all()
    if all_same_sign and total != 0:
        lines.append(f"• Top 20% of records account for {_pct(top20.sum(), total)} of total {num}.")
    elif not all_same_sign:
        lines.append(f"• Values include both positive and negative {num} — "
                     "concentration share is not meaningful here. "
                     f"Top single value: {_fmt(s.max())}, lowest: {_fmt(s.min())}.")

    # Group breakdown
    if cat:
        agg = df.groupby(cat, dropna=False)[num].agg(["sum","mean","count"]).dropna()
        agg.columns = ["total","avg","count"]
        agg = agg.sort_values("total", ascending=False)

        lines.append(f"\n**Top performers by {cat}:**")
        for grp, row in agg.head(5).iterrows():
            share = 100 * row["total"] / total if total else 0
            lines.append(f"  🏆 {grp}: {_fmt(row['total'])} ({share:.1f}%),  avg {_fmt(row['avg'])},  n={int(row['count'])}")

        if len(agg) > 3:
            lines.append(f"\n**Lowest performers by {cat}:**")
            for grp, row in agg.tail(3).iterrows():
                share = 100 * row["total"] / total if total else 0
                lines.append(f"  🔻 {grp}: {_fmt(row['total'])} ({share:.1f}%),  avg {_fmt(row['avg'])}")

        # Concentration check (only meaningful if not an ID column)
        top1 = 100 * agg["total"].iloc[0] / total if total else 0
        if top1 >= 40 and len(agg) >= 3:
            lines.append(f"\n⚠️ '{agg.index[0]}' accounts for {top1:.0f}% of {num}. "
                         "High concentration — understand why this group dominates.")

    return lines


def _trend_analysis(p: DataProfile) -> list[str]:
    df  = p.df
    num = p.value_col
    lines = [f"**Trend Analysis — {num or 'data'}**"]

    if not num:
        return lines + ["No numeric column found for trend analysis."]

    if not p.date_col:
        # No date — use record order
        s = _series(df, num).reset_index(drop=True)
        n = len(s)
        if n < 6:
            return lines + ["Not enough records for trend analysis (need at least 6)."]
        q = max(n//4, 1)
        periods = [s.iloc[:q].mean(), s.iloc[q:2*q].mean(),
                   s.iloc[2*q:3*q].mean(), s.iloc[3*q:].mean()]
        labels  = ["Earliest 25%","Early-mid 25%","Late-mid 25%","Most recent 25%"]
        lines.append("(No date column — using record order as time proxy)")
        for lbl, val in zip(labels, periods):
            lines.append(f"  {lbl}: {_fmt(val)}")
        chg  = _chg(periods[-1], periods[0])
        word = "increased" if periods[-1] > periods[0] else "decreased"
        lines.append(f"\n• {num} has {word} {chg} from earliest to most recent records.")
        if periods[-1] < periods[0] * 0.85:
            lines.append("⚠️ Notable decline — investigate what changed over time.")
        elif periods[-1] > periods[0] * 1.1:
            lines.append("✅ Clear upward trend — identify what is driving improvement.")
        return lines

    dc  = p.date_col
    tmp = df.copy()
    tmp[dc] = pd.to_datetime(tmp[dc], errors="coerce")
    tmp = tmp.dropna(subset=[dc, num]).sort_values(dc)
    tmp[num] = pd.to_numeric(tmp[num], errors="coerce")
    days = (tmp[dc].max() - tmp[dc].min()).days

    if   days > 365:  code, label = "Q", "quarter"
    elif days > 60:   code, label = "M", "month"
    elif days > 14:   code, label = "W", "week"
    else:             code, label = "D", "day"

    tmp["_p"] = tmp[dc].dt.to_period(code).astype(str)
    agg = tmp.groupby("_p")[num].sum().dropna()

    lines.append(f"• Date range: {tmp[dc].min().date()} → {tmp[dc].max().date()} ({days} days)")
    lines.append(f"• Aggregated by {label} — {len(agg)} periods")

    if len(agg) < 2:
        return lines + ["Need at least 2 periods for trend analysis."]

    chg  = _chg(agg.iloc[-1], agg.iloc[0])
    word = "▲ up" if agg.iloc[-1] >= agg.iloc[0] else "▼ down"
    lines.append(f"\n• Overall: {word} {chg} (first → last {label})")
    lines.append(f"  First {label} ({agg.index[0]}):  {_fmt(agg.iloc[0])}")
    lines.append(f"  Last  {label} ({agg.index[-1]}): {_fmt(agg.iloc[-1])}")
    lines.append(f"  Peak  {label}: {agg.idxmax()} → {_fmt(agg.max())}")
    lines.append(f"  Trough {label}: {agg.idxmin()} → {_fmt(agg.min())}")

    # Volatility
    cv = agg.std() / agg.mean() if agg.mean() else 0
    if cv > 0.3:
        lines.append(f"\n⚠️ High variability (CV={cv:.2f}) — significant fluctuation between periods.")
    else:
        lines.append(f"\n✅ Stable trend (CV={cv:.2f}) — consistent values across periods.")

    # Recent momentum
    if len(agg) >= 3:
        mom = _chg(agg.iloc[-1], agg.iloc[-2])
        if agg.iloc[-1] < agg.iloc[-2] * 0.85:
            lines.append(f"⚠️ Last {label} dropped {mom} vs previous — recent downturn.")
        elif agg.iloc[-1] > agg.iloc[-2] * 1.15:
            lines.append(f"🚀 Last {label} up {mom} vs previous — recent acceleration.")

    return lines


def _segment_analysis(p: DataProfile) -> list[str]:
    df  = p.df
    num = p.value_col
    cat = p.group_cols[0] if p.group_cols else None

    if not cat or not num:
        return [
            "Segment analysis requires at least one categorical (text) column for grouping.",
            f"Your dataset has {len(p.numeric_cols)} numeric column(s) but no suitable categorical grouper. ",
            "Try adding a column like 'Category', 'Region', 'Type', or 'Group' to enable segment analysis.",
            f"Available columns: {', '.join(df.columns.tolist())}",
        ]

    lines = [f"**Segment Analysis — {num} by {cat}**"]
    agg = df.groupby(cat, dropna=False)[num].agg(["sum","mean","count","std"]).dropna()
    agg.columns = ["total","avg","count","std"]
    agg = agg.sort_values("total", ascending=False)
    grand = agg["total"].sum()

    lines.append(f"• {agg.shape[0]} unique values in '{cat}'  |  Grand total {num}: {_fmt(grand)}")
    lines.append(f"\n**Breakdown:**")
    cum = 0
    for i, (grp, row) in enumerate(agg.iterrows()):
        share = 100 * row["total"] / grand if grand else 0
        cum  += share
        marker = "  ← 80% cumulative" if cum >= 80 and (cum - share) < 80 else ""
        lines.append(
            f"  {i+1}. {grp}: {_fmt(row['total'])} ({share:.1f}%),  "
            f"avg={_fmt(row['avg'])},  n={int(row['count'])}{marker}"
        )

    # Second grouper comparison if available
    if len(p.group_cols) >= 2:
        cat2 = p.group_cols[1]
        lines.append(f"\n**Cross-analysis: {num} by {cat} × {cat2}**")
        pivot = df.groupby([cat, cat2], dropna=False)[num].sum().unstack(fill_value=0)
        for grp in pivot.index[:5]:
            row_vals = pivot.loc[grp]
            top_sub  = row_vals.idxmax()
            lines.append(f"  {grp}: highest in '{top_sub}' ({_fmt(row_vals[top_sub])})")

    return lines


def _opportunity_analysis(p: DataProfile) -> list[str]:
    df  = p.df
    num = p.value_col
    cat = p.group_cols[0] if p.group_cols else None

    lines = [f"**Opportunity Analysis — {num or 'data'}**"]

    if not num:
        return lines + ["No numeric column found."]

    if not cat:
        # No categorical — do percentile-based opportunity analysis
        s = _series(df, num)
        p90 = s.quantile(0.9)
        p10 = s.quantile(0.1)
        below_avg = s[s < s.mean()]
        lines.append(f"• Top 10% of records have {num} ≥ {_fmt(p90)}")
        lines.append(f"• Bottom 10% of records have {num} ≤ {_fmt(p10)}")
        lines.append(f"• {len(below_avg):,} records ({_pct(len(below_avg),len(s))}) are below average")
        lines.append(f"\n💡 Opportunity: if below-average records reached the average, "
                     f"total would increase by ~{_fmt((s.mean()-below_avg.mean())*len(below_avg))}")
        return lines

    agg = df.groupby(cat, dropna=False)[num].agg(["sum","mean","count"]).dropna()
    agg.columns = ["total","avg","count"]
    grand   = agg["total"].sum()
    avg_all = agg["avg"].mean()

    # Volume vs Value matrix
    lines.append(f"\n**Volume vs Value matrix — {cat}:**")
    for grp, row in agg.sort_values("total", ascending=False).iterrows():
        v_high = row["count"] >= agg["count"].median()
        a_high = row["avg"]   >= avg_all
        tag = {
            (True,  True):  "✅ Core — high activity + high value. Protect and scale.",
            (True,  False): "🎯 Leverage — high activity, low avg value. Increase value per record.",
            (False, True):  "💎 Premium — low activity, high value. Grow frequency/volume.",
            (False, False): "⚠️ Weak — low activity + low value. Review or exit.",
        }[(v_high, a_high)]
        lines.append(
            f"  {grp}: {int(row['count']):,} records @ avg {_fmt(row['avg'])}, "
            f"total {_fmt(row['total'])} ({_pct(row['total'],grand)}) — {tag}"
        )

    # Upside calculation
    top_avg = agg["avg"].max()
    upside  = sum((top_avg - row["avg"]) * row["count"]
                  for _, row in agg.iterrows() if row["avg"] < top_avg)
    if upside > 0:
        lines.append(f"\n💡 Gap opportunity: if all groups reached the top avg ({_fmt(top_avg)}), "
                     f"total {num} could increase by ~{_fmt(upside)} ({_pct(upside, grand)} more).")

    # Time-based growth per group
    if p.date_col:
        dc  = p.date_col
        tmp = df.copy()
        tmp[dc] = pd.to_datetime(tmp[dc], errors="coerce")
        tmp = tmp.dropna(subset=[dc]).sort_values(dc)
        half = tmp[dc].quantile(0.5)
        h1 = tmp[tmp[dc] <= half].groupby(cat, dropna=False)[num].sum()
        h2 = tmp[tmp[dc] >  half].groupby(cat, dropna=False)[num].sum()
        both = pd.DataFrame({"h1":h1,"h2":h2}).dropna()
        both["chg"] = (both["h2"]-both["h1"]) / both["h1"].abs().replace(0,np.nan) * 100
        both = both.dropna(subset=["chg"]).sort_values("chg", ascending=False)
        if not both.empty:
            lines.append(f"\n**Growth by {cat} (first half vs second half of period):**")
            for grp, row in both.iterrows():
                arrow  = "📈" if row["chg"] >= 0 else "📉"
                action = "— accelerating" if row["chg"] > 15 else \
                         ("— declining, investigate" if row["chg"] < -15 else "— stable")
                lines.append(f"  {arrow} {grp}: {row['chg']:+.1f}% {action}")

    return lines


def _anomaly_analysis(p: DataProfile) -> list[str]:
    df    = p.df
    lines = ["**Anomaly & Quality Analysis**"]
    found = 0

    # 1. Missing values
    missing     = int(df.isna().sum().sum())
    total_cells = p.rows * p.cols_count
    dups        = int(df.duplicated().sum())

    if missing:
        worst = df.isna().sum().sort_values(ascending=False)
        worst = worst[worst > 0]
        lines.append(f"⚠️ Missing values: {missing:,} ({_pct(missing, total_cells)}) across {len(worst)} column(s).")
        for col, cnt in worst.head(3).items():
            lines.append(f"  • '{col}': {cnt:,} missing ({_pct(cnt, p.rows)})")
        found += 1
    else:
        lines.append("✅ No missing values — dataset is complete.")

    if dups:
        lines.append(f"⚠️ {dups:,} duplicate rows ({_pct(dups, p.rows)}) — "
                     "may inflate totals. Remove on Cleaning page.")
        found += 1
    else:
        lines.append("✅ No duplicate rows.")

    # 2. Statistical outliers per numeric column
    outlier_found = False
    for col in p.numeric_cols[:6]:
        s = _series(df, col)
        if len(s) < 8:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        if iqr <= 0:
            continue
        extreme = s[(s < q1 - 3*iqr) | (s > q3 + 3*iqr)]
        if not extreme.empty:
            lines.append(f"⚠️ '{col}': {len(extreme):,} extreme value(s) — "
                         f"range {_fmt(extreme.min())} to {_fmt(extreme.max())} "
                         f"(normal range: {_fmt(q1-1.5*iqr)} – {_fmt(q3+1.5*iqr)}). "
                         "Verify these are real, not data entry errors.")
            outlier_found = True
            found += 1

    if not outlier_found:
        lines.append("✅ No extreme outliers detected in numeric columns.")

    # 3. Constant columns (no useful information)
    constants = [c for c in p.numeric_cols if _series(df, c).nunique() <= 1]
    if constants:
        lines.append(f"⚠️ Constant columns (single value, no information): {', '.join(constants)}")
        found += 1

    # 4. High cardinality text columns (possible ID columns)
    for col in p.cat_cols:
        ratio = df[col].nunique() / p.rows
        if ratio > 0.8:
            lines.append(f"⚠️ '{col}' has {df[col].nunique():,} unique values ({ratio:.0%} of rows) — "
                         "likely an ID or free-text field. Not useful for grouping.")
            found += 1
            break  # just flag one

    if found == 0:
        lines.append("\n✅ Data looks clean and well-structured overall.")

    return lines


def _correlation_analysis(p: DataProfile) -> list[str]:
    df   = p.df
    nums = p.numeric_cols
    lines = ["**Correlation Analysis — Which numbers move together?**"]

    if len(nums) < 2:
        return lines + ["Need at least 2 numeric columns for correlation analysis."]

    # Exclude ID-like columns
    good_nums = []
    for col in nums[:10]:
        s = _series(df, col)
        if s.nunique() > 1 and not (s.is_monotonic_increasing and s.nunique() == len(s)):
            good_nums.append(col)

    if len(good_nums) < 2:
        return lines + ["Not enough non-ID numeric columns for correlation."]

    corr = df[good_nums].corr(numeric_only=True)
    pairs = []
    for i in range(len(good_nums)):
        for j in range(i+1, len(good_nums)):
            v = corr.iloc[i,j]
            if not math.isnan(v):
                pairs.append((good_nums[i], good_nums[j], v))

    pairs.sort(key=lambda x: abs(x[2]), reverse=True)

    strong  = [(a,b,r) for a,b,r in pairs if abs(r) >= 0.7]
    moderate = [(a,b,r) for a,b,r in pairs if 0.4 <= abs(r) < 0.7]
    weak     = [(a,b,r) for a,b,r in pairs if abs(r) < 0.4]

    if strong:
        lines.append(f"\n**Strong correlations (|r| ≥ 0.7):**")
        for a, b, r in strong[:5]:
            direction = "positive" if r > 0 else "negative"
            lines.append(f"  • {a} ↔ {b}: r={r:.3f} — strong {direction} relationship. "
                         f"{'One tends to increase with the other.' if r>0 else 'One tends to increase as the other decreases.'}")
    if moderate:
        lines.append(f"\n**Moderate correlations (0.4 ≤ |r| < 0.7):**")
        for a, b, r in moderate[:4]:
            lines.append(f"  • {a} ↔ {b}: r={r:.3f}")
    if not strong and not moderate:
        lines.append("• No strong correlations found. Variables appear largely independent.")
    lines.append(f"\n• Weakly correlated pairs: {len(weak)} (|r| < 0.4) — no meaningful relationship.")
    return lines


def _action_summary(p: DataProfile) -> list[str]:
    df    = p.df
    num   = p.value_col
    cat   = p.group_cols[0] if p.group_cols else None
    lines = [f"**Top Actions — {p.domain.title()} Data**"]
    actions = []
    idx = 1

    # 1. Data quality
    missing = int(df.isna().sum().sum())
    dups    = int(df.duplicated().sum())
    if missing:
        worst = df.isna().sum().idxmax()
        cnt   = int(df[worst].isna().sum())
        actions.append(f"{idx}. 🧹 **Fix missing data in '{worst}'** ({cnt:,} missing values). "
                       "Go to Cleaning → Fill or Drop. Analysis on incomplete data gives wrong answers.")
        idx += 1
    if dups:
        actions.append(f"{idx}. 🧹 **Remove {dups:,} duplicate rows** — "
                       "they double-count your totals. Cleaning → Remove duplicates.")
        idx += 1

    # 2. Key metric action
    if num:
        s  = _series(df, num)
        cv = s.std() / s.mean() if s.mean() else 0
        if cv > 0.6:
            p10 = s.quantile(0.1)
            p90 = s.quantile(0.9)
            actions.append(f"{idx}. 📊 **High variability in '{num}'** (CV={cv:.2f}). "
                           f"Values range from {_fmt(p10)} (10th pct) to {_fmt(p90)} (90th pct). "
                           "Investigate why some records are much higher/lower than others.")
            idx += 1

    # 3. Segment action
    if num and cat:
        agg   = df.groupby(cat, dropna=False)[num].sum().sort_values(ascending=False).dropna()
        grand = agg.sum()
        if grand > 0 and len(agg) >= 2:
            top1_share = agg.iloc[0]/grand*100
            bottom_share = agg.iloc[-1]/grand*100
            actions.append(
                f"{idx}. 🎯 **'{agg.index[0]}' leads {cat}** ({top1_share:.0f}% of {num}). "
                f"Understand what makes it top-performing and apply those factors elsewhere. "
                f"'{agg.index[-1]}' is the lowest ({bottom_share:.1f}%) — review why."
            )
            idx += 1

    # 4. Trend action
    if num and p.date_col:
        dc  = p.date_col
        tmp = df[[dc, num]].copy()
        tmp[dc] = pd.to_datetime(tmp[dc], errors="coerce")
        tmp[num] = pd.to_numeric(tmp[num], errors="coerce")
        tmp = tmp.dropna().sort_values(dc)
        if len(tmp) >= 6:
            n     = max(len(tmp)//4, 1)
            first = tmp[num].iloc[:n].mean()
            last  = tmp[num].iloc[-n:].mean()
            if pd.notna(first) and pd.notna(last) and first > 0:
                chg = (last-first)/abs(first)*100
                if chg < -15:
                    actions.append(f"{idx}. 📉 **'{num}' is down {abs(chg):.1f}%** from earliest to latest records. "
                                   "Use Visualization → Trend chart to pinpoint when the decline started.")
                elif chg > 15:
                    actions.append(f"{idx}. 🚀 **'{num}' is up {chg:.1f}%** — positive trend. "
                                   "Identify what changed and sustain it.")
                idx += 1

    # 5. Outlier action
    if num:
        s = _series(df, num)
        if len(s) >= 8:
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                ext = s[s > q3 + 3*iqr]
                if not ext.empty:
                    actions.append(f"{idx}. ⚠️ **Verify {len(ext):,} extreme '{num}' value(s)** "
                                   f"(up to {_fmt(ext.max())}). "
                                   "Confirm these are real records, not data entry errors.")
                    idx += 1

    # 6. Correlation action if multiple numerics
    if len(p.numeric_cols) >= 3:
        good = [c for c in p.numeric_cols[:8] if _series(df,c).nunique() > 1]
        if len(good) >= 2:
            corr = df[good].corr(numeric_only=True)
            best_pair = None
            best_r    = 0
            for i in range(len(good)):
                for j in range(i+1, len(good)):
                    v = abs(corr.iloc[i,j])
                    if not math.isnan(v) and v > best_r:
                        best_r = v
                        best_pair = (good[i], good[j], corr.iloc[i,j])
            if best_pair and best_r >= 0.6:
                a, b, r = best_pair
                direction = "positively" if r > 0 else "negatively"
                actions.append(f"{idx}. 🔗 **'{a}' and '{b}' are {direction} correlated (r={r:.2f})**. "
                               "Use this relationship — improving one likely affects the other.")
                idx += 1

    # Always end with monitoring
    actions.append(f"{idx}. 📋 **Set a regular review cycle** — reload fresh data periodically, "
                   "run Trend + Segment analysis, compare vs prior period. "
                   "Consistent monitoring catches problems early.")

    return lines + actions


# ═══════════════════════════════════════════════════════════════════════════════
#  ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

_ROUTES = [
    (r"overview|summary|describe|what is|tell me about|show me",              "overview"),
    (r"perform|revenue|sales|score|output|production|top|best|highest|worst", "performance"),
    (r"trend|over time|growth|decline|month|quarter|year|period|time|when",   "trend"),
    (r"segment|region|group|category|by|breakdown|split|compare|ward|class",  "segment"),
    (r"opportunit|grow|potential|gap|improve|upside|leverage|untap|scale",    "opportunity"),
    (r"anomal|outlier|error|quality|missing|duplicate|clean|check|verify",    "anomaly"),
    (r"correlat|relation|link|connect|together|depend|affect|cause",          "correlation"),
    (r"action|recommend|what.*do|next step|do now|advice|suggest|help|start", "actions"),
    (r"risk|danger|warn|concentrat|vulnerab|fragile|exposure|problem",        "actions"),
    (r"profit|margin|cost|expense|loss|net|break.?even",                      "performance"),
    (r"price|pricing|rate|fee|charge|discount|tariff",                        "performance"),
]


def _route(query: str) -> str:
    q = query.lower()
    for pattern, label in _ROUTES:
        if re.search(pattern, q):
            return label
    return "actions"


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def generate_insight(query: str, df: "pd.DataFrame | None" = None) -> str:
    if not query:
        return "Ask a question about your data — e.g. 'show me trends' or 'what should I do now?'"
    if df is None or df.empty:
        return "No dataset loaded. Upload data on the Ingestion page first."

    try:
        df    = _coerce(df)
        p     = DataProfile(df, query)
        route = _route(query)

        dispatch = {
            "overview":     lambda: _overview(p),
            "performance":  lambda: _performance_analysis(p),
            "trend":        lambda: _trend_analysis(p),
            "segment":      lambda: _segment_analysis(p),
            "opportunity":  lambda: _opportunity_analysis(p),
            "anomaly":      lambda: _anomaly_analysis(p),
            "correlation":  lambda: _correlation_analysis(p),
            "actions":      lambda: _action_summary(p),
        }

        lines = dispatch.get(route, dispatch["actions"])()
        return "\n".join(lines)

    except Exception as e:
        import traceback
        return (f"Analysis error: {e}\n\n"
                f"Dataset: {df.shape[0]} rows × {df.shape[1]} cols\n"
                f"Columns: {', '.join(df.columns.tolist())}\n\n"
                f"Please check your data has at least one numeric column.\n\n"
                f"Details: {traceback.format_exc()}")
