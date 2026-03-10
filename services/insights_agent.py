import pandas as pd
import requests

from config.settings import HUGGINGFACE_API_KEY, HUGGINGFACE_MODEL


def _build_dataset_context(df: pd.DataFrame) -> str:
    rows = len(df)
    columns = list(df.columns)
    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    non_numeric_columns = df.select_dtypes(exclude="number").columns.tolist()

    summary_lines = [
        f"Rows: {rows}",
        f"Columns: {columns}",
        f"Numeric columns: {numeric_columns}",
        f"Categorical/text columns: {non_numeric_columns}",
    ]

    if numeric_columns:
        summary_table = df[numeric_columns].describe().round(3).to_string()
        summary_lines.append("Numeric summary:")
        summary_lines.append(summary_table)

    return "\n".join(summary_lines)


def _call_huggingface(prompt: str) -> str:
    if not HUGGINGFACE_API_KEY:
        return ""

    url = f"https://api-inference.huggingface.co/models/{HUGGINGFACE_MODEL}"
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 240,
            "temperature": 0.3,
            "return_full_text": False,
        },
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list) and data and isinstance(data[0], dict):
            if "generated_text" in data[0]:
                return data[0]["generated_text"].strip()

        if isinstance(data, dict):
            if "error" in data:
                return f"Model error: {data['error']}"
            if "generated_text" in data:
                return str(data["generated_text"]).strip()

        return "The model returned an unexpected response format."
    except requests.RequestException as exc:
        return f"__HF_ERROR__ {exc}"


def _build_local_insight(query: str, df: pd.DataFrame) -> str:
    rows = len(df)
    columns = len(df.columns)
    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    categorical_columns = df.select_dtypes(exclude="number").columns.tolist()
    missing_cells = int(df.isna().sum().sum())

    insights = [
        f"- Dataset has {rows:,} rows and {columns} columns.",
        f"- Numeric columns: {len(numeric_columns)} | Categorical/text columns: {len(categorical_columns)}.",
        f"- Missing values detected: {missing_cells:,}.",
    ]

    for col in numeric_columns[:4]:
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if series.empty:
            continue
        insights.append(
            f"- {col}: sum={series.sum():,.2f}, avg={series.mean():,.2f}, min={series.min():,.2f}, max={series.max():,.2f}."
        )

    for col in categorical_columns[:3]:
        series = df[col].dropna().astype(str)
        if series.empty:
            continue
        top_values = series.value_counts().head(3)
        top_text = ", ".join([f"{k} ({v})" for k, v in top_values.items()])
        insights.append(f"- {col}: top values are {top_text}.")

    insights.append(f"- Question interpreted: {query}")
    insights.append("- Insight mode: local analytics fallback (no API token required).")

    return "\n".join(insights)


def generate_insight(query: str, df: pd.DataFrame | None = None) -> str:
    if not query:
        return "Please enter a question to generate insights."

    if df is None or df.empty:
        return "No dataset is available for insight generation. Upload data first."

    context = _build_dataset_context(df)
    prompt = (
        "You are a senior business analyst. "
        "Answer clearly and practically in 4-8 bullet points. "
        "Use only the provided dataset context. "
        "If evidence is insufficient, say so briefly.\n\n"
        f"Dataset context:\n{context}\n\n"
        f"User question: {query}\n\n"
        "Insight answer:"
    )

    model_answer = _call_huggingface(prompt)
    if not model_answer:
        return _build_local_insight(query=query, df=df)

    if model_answer.startswith("__HF_ERROR__"):
        fallback = _build_local_insight(query=query, df=df)
        return f"Live model unavailable ({model_answer.replace('__HF_ERROR__', '').strip()}).\n\n{fallback}"

    return model_answer
