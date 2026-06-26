import io
import zipfile
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak
)


def format_compact_number(
    value: float, number_format: str = "plain", currency: str = "USD"
) -> str:
    if pd.isna(value):
        return "N/A"
    prefix = ""
    if number_format == "currency":
        symbols = {
            "USD": "$", "EUR": "€", "GBP": "£",
            "KES": "KSh ", "INR": "₹", "JPY": "¥",
        }
        prefix = symbols.get(currency, f"{currency} ")
    if number_format == "k":
        return f"{prefix}{value / 1_000:,.2f}K"
    if number_format == "m":
        return f"{prefix}{value / 1_000_000:,.2f}M"
    if number_format == "b":
        return f"{prefix}{value / 1_000_000_000:,.2f}B"
    if number_format == "currency":
        return f"{prefix}{value:,.2f}"
    return f"{value:,.2f}"


def build_exhaustive_report_data(
    df: pd.DataFrame, source_name: str = "dataset"
) -> dict:
    report_df = df.copy()
    for col in report_df.select_dtypes(include="object").columns:
        parsed = pd.to_numeric(report_df[col], errors="coerce")
        if parsed.notna().mean() >= 0.8:
            report_df[col] = parsed

    rows = len(report_df)
    cols = len(report_df.columns)
    missing_cells = int(report_df.isna().sum().sum())
    missing_pct = (missing_cells / max(rows * max(cols, 1), 1)) * 100
    numeric_cols = report_df.select_dtypes(include="number").columns.tolist()
    categorical_cols = report_df.select_dtypes(exclude="number").columns.tolist()

    overview = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": source_name,
        "rows": rows,
        "columns": cols,
        "numeric_columns": len(numeric_cols),
        "categorical_columns": len(categorical_cols),
        "missing_values": missing_cells,
        "missing_percent": round(missing_pct, 3),
        "column_names": report_df.columns.tolist(),
    }

    numeric_summary = pd.DataFrame()
    if numeric_cols:
        numeric_summary = (
            report_df[numeric_cols]
            .describe()
            .transpose()
            .reset_index()
            .rename(columns={"index": "column"})
        )
        numeric_summary["range"] = numeric_summary["max"] - numeric_summary["min"]

    categorical_summary_rows = []
    for col in categorical_cols:
        series = report_df[col].dropna().astype(str)
        if series.empty:
            top_value, top_freq, unique_count = "N/A", 0, 0
        else:
            vc = series.value_counts()
            top_value = vc.index[0]
            top_freq = int(vc.iloc[0])
            unique_count = int(series.nunique())
        categorical_summary_rows.append({
            "column": col,
            "unique_values": unique_count,
            "top_value": top_value,
            "top_frequency": top_freq,
            "missing": int(report_df[col].isna().sum()),
        })
    categorical_summary = pd.DataFrame(categorical_summary_rows)
    sample_rows = report_df.head(20)

    return {
        "overview": overview,
        "numeric_summary": numeric_summary,
        "categorical_summary": categorical_summary,
        "sample_rows": sample_rows,
    }


def report_data_to_html(report_data: dict) -> str:
    overview = report_data["overview"]
    chunks = [
        "<html><head><meta charset='utf-8'><title>DericBI Report</title></head><body>",
        "<h1>Dynamic Dataset Report</h1>",
        f"<p><b>Generated:</b> {overview['generated_at']}</p>",
        f"<p><b>Source:</b> {overview['source']}</p>",
        "<h2>Overview</h2><ul>",
        f"<li>Rows: {overview['rows']:,}</li>",
        f"<li>Columns: {overview['columns']}</li>",
        f"<li>Numeric columns: {overview['numeric_columns']}</li>",
        f"<li>Categorical columns: {overview['categorical_columns']}</li>",
        f"<li>Missing values: {overview['missing_values']:,} "
        f"({overview['missing_percent']:.2f}%)</li>",
        "</ul>",
    ]
    ns = report_data["numeric_summary"]
    if not ns.empty:
        chunks += ["<h2>Numeric Summary</h2>", ns.to_html(index=False, border=1)]
    cs = report_data["categorical_summary"]
    if not cs.empty:
        chunks += ["<h2>Categorical Summary</h2>", cs.to_html(index=False, border=1)]
    sr = report_data["sample_rows"]
    if not sr.empty:
        chunks += ["<h2>Sample Rows (Top 20)</h2>", sr.to_html(index=False, border=1)]
    chunks.append("</body></html>")
    return "\n".join(chunks)


def report_data_to_pdf_bytes(report_data: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    overview = report_data["overview"]
    story.append(Paragraph("Dynamic Dataset Report", styles["Title"]))
    story.append(Spacer(1, 0.2 * inch))
    for line in [
        f"Generated: {overview['generated_at']}",
        f"Source: {overview['source']}",
        f"Rows: {overview['rows']:,}",
        f"Columns: {overview['columns']}",
        f"Numeric columns: {overview['numeric_columns']}",
        f"Categorical columns: {overview['categorical_columns']}",
        f"Missing values: {overview['missing_values']:,} "
        f"({overview['missing_percent']:.2f}%)",
    ]:
        story.append(Paragraph(line, styles["BodyText"]))
    story.append(Spacer(1, 0.2 * inch))

    def add_table(title, frame, max_rows=25):
        if frame.empty:
            return
        story.append(Paragraph(title, styles["Heading2"]))
        limited = frame.head(max_rows).copy()
        for c in limited.columns:
            limited[c] = limited[c].astype(str)
        data = [limited.columns.tolist()] + limited.values.tolist()
        tbl = Table(data, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.15 * inch))

    add_table("Numeric Summary",     report_data["numeric_summary"],     30)
    add_table("Categorical Summary", report_data["categorical_summary"], 40)
    add_table("Sample Rows",         report_data["sample_rows"],         20)
    doc.build(story)
    return buffer.getvalue()


def visuals_to_html(figures: list, title: str = "Visualizations") -> str:
    parts = [
        "<html><head><meta charset='utf-8'>"
        "<title>Visualization Export</title></head><body>",
        f"<h1>{title}</h1>",
    ]
    for idx, fig in enumerate(figures, 1):
        parts.append(f"<h2>Figure {idx}</h2>")
        parts.append(fig.to_html(full_html=False, include_plotlyjs="cdn"))
    parts.append("</body></html>")
    return "\n".join(parts)


def visuals_to_pdf_bytes(figures: list, title: str = "Visualizations") -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]), Spacer(1, 0.2 * inch)]
    for idx, fig in enumerate(figures, 1):
        story.append(Paragraph(f"Figure {idx}", styles["Heading2"]))
        img_bytes = pio.to_image(fig, format="png", width=1400, height=800, scale=1)
        img = Image(io.BytesIO(img_bytes), width=9.5 * inch, height=5.2 * inch)
        story.append(img)
        if idx < len(figures):
            story.append(PageBreak())
    doc.build(story)
    return buffer.getvalue()


def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="cleaned_data")
    return output.getvalue()


def figures_to_zip_bytes(figures: list) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for idx, fig in enumerate(figures, 1):
            zf.writestr(
                f"figure_{idx}.html",
                fig.to_html(full_html=True, include_plotlyjs="cdn"),
            )
    return output.getvalue()
