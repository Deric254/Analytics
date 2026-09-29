"""
DericBI AI Assistant
====================
Thin wrapper that calls whichever free AI API key is configured.
Priority: NVIDIA NIM → Gemini (Google) → Groq → OpenRouter → local fallback
(no key needed). All four remote providers retry once on a transient
failure (503 "overloaded" or a timeout) before moving to the next one.

Set ONE of these environment variables (on Render: Environment → Add variable):
  NVIDIA_API_KEY   — https://build.nvidia.com                (free tier)
  GEMINI_API_KEY   — https://aistudio.google.com/apikey       (free, generous)
  GROQ_API_KEY     — https://console.groq.com                 (free, very fast)
  OPENROUTER_KEY   — https://openrouter.ai                    (free tier, many models)

If none is set, the assistant still works using the local insights engine.
"""

import os
import json
import requests
import pandas as pd
from services.insights_agent import DataProfile, _coerce, generate_insight


# ── Dataset context builder ───────────────────────────────────────────────────

def build_context(df: pd.DataFrame) -> str:
    """Build a compact data context string the AI can use to answer questions."""
    if df is None or df.empty:
        return "No dataset is currently loaded."

    df2 = _coerce(df)
    p   = DataProfile(df2)
    rows, cols = df2.shape
    missing = int(df2.isna().sum().sum())

    num_cols = df2.select_dtypes(include="number").columns.tolist()
    cat_cols = p.cat_cols

    lines = [
        f"Dataset: {rows:,} rows × {cols} columns. Domain: {p.domain}.",
        f"Numeric columns: {', '.join(num_cols[:8])}.",
        f"Categorical columns: {', '.join(cat_cols[:6])}.",
        f"Date columns: {', '.join(p.date_cols[:3])}." if p.date_cols else "",
        f"Missing values: {missing:,}. Duplicates: {int(df2.duplicated().sum())}.",
        f"Key metric: {p.value_col}. Main groups: {', '.join(p.group_cols)}.",
    ]

    # Add quick stats on the key metric plus up to 2 other numeric columns —
    # broader grounding so the AI can answer questions about columns beyond
    # just the single "primary" metric without inventing numbers for them.
    stat_cols = [c for c in ([p.value_col] if p.value_col else []) + num_cols if c][:3]
    seen = set()
    for col in stat_cols:
        if col in seen or col not in df2.columns:
            continue
        seen.add(col)
        s = pd.to_numeric(df2[col], errors="coerce").dropna()
        if not s.empty:
            lines.append(
                f"{col} stats: total={s.sum():,.2f}, mean={s.mean():,.2f}, "
                f"min={s.min():,.2f}, max={s.max():,.2f}."
            )

    # Add top group if available
    if p.value_col and p.group_cols:
        cat = p.group_cols[0]
        try:
            top = df2.groupby(cat)[p.value_col].sum().sort_values(ascending=False)
            top3 = ", ".join(f"{k}: {v:,.2f}" for k, v in top.head(3).items())
            lines.append(f"Top {cat} by {p.value_col}: {top3}.")
        except Exception:
            pass

    return " ".join(l for l in lines if l)


def _system_prompt(context: str) -> str:
    return f"""You are DericBI, an expert business intelligence analyst embedded in the DericBI Analytics platform.

You have full context of the user's current dataset:
{context}

Your role:
- Answer questions about this specific data
- Explain analytical concepts clearly (teach when asked)
- Give business-oriented insights, not just statistics
- When asked to predict, use the data context to give a reasoned forecast
- Keep responses concise and actionable — 3-5 sentences unless more detail is requested
- Never make up data points not supported by the context above
- If asked to build something, describe exactly what steps to take in DericBI

Always be direct, professional, and focused on business value."""


# ── API callers ───────────────────────────────────────────────────────────────

# Gemini 1.5 models were fully shut down in 2026 (404 on every call).
# gemini-flash-latest is Google's auto-updated alias that always points to
# the current stable Flash model, so this doesn't need updating again.
GEMINI_MODEL = "gemini-flash-latest"


def _call_gemini(question: str, context: str) -> tuple[str, str]:
    """
    Returns (answer, error). answer is None if the call failed; error explains why.
    Retries once on a transient failure (503 "model overloaded" or a timeout) —
    these usually clear within a second or two, so one retry avoids an
    unnecessary drop to the local engine for what is often a momentary blip.
    """
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return None, "no key configured"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={key}"
    payload = {
        "contents": [{
            "parts": [{"text": _system_prompt(context) + f"\n\nUser: {question}"}]
        }],
        "generationConfig": {"maxOutputTokens": 512, "temperature": 0.4},
    }

    last_error = None
    for attempt in range(2):
        try:
            r = requests.post(url, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip(), None
        except requests.exceptions.HTTPError as e:
            last_error = f"Gemini is temporarily busy (HTTP {e.response.status_code})"
            if e.response.status_code != 503 or attempt == 1:
                break
        except requests.exceptions.Timeout:
            last_error = "Gemini took too long to respond"
            if attempt == 1:
                break
        except Exception as e:
            last_error = f"Gemini connection issue: {e}"
            break

    return None, last_error


def _call_openai_compatible(name: str, url: str, model: str, api_key: str,
                             question: str, context: str,
                             extra_headers: dict | None = None) -> tuple[str, str]:
    """
    Shared caller for every OpenAI-compatible chat-completions endpoint
    (NVIDIA NIM, Groq, OpenRouter all speak this exact same request/response
    shape). One retry on a transient failure (503 or a timeout), same as
    Gemini's caller — previously Groq and OpenRouter each gave up
    immediately on any failure with no retry, which was inconsistent with
    Gemini's more resilient behavior for no real reason.
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _system_prompt(context)},
            {"role": "user", "content": question},
        ],
        "max_tokens": 512,
        "temperature": 0.4,
    }

    last_error = None
    for attempt in range(2):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=25)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip(), None
        except requests.exceptions.HTTPError as e:
            last_error = f"{name} API error: {e.response.status_code} {e.response.text[:150]}"
            if e.response.status_code != 503 or attempt == 1:
                break
        except requests.exceptions.Timeout:
            last_error = f"{name} took too long to respond"
            if attempt == 1:
                break
        except Exception as e:
            last_error = f"{name} call failed: {e}"
            break

    return None, last_error


def _call_nvidia(question: str, context: str) -> tuple[str, str]:
    key = os.getenv("NVIDIA_API_KEY", "").strip()
    if not key:
        return None, "no key configured"
    return _call_openai_compatible(
        "NVIDIA", "https://integrate.api.nvidia.com/v1/chat/completions",
        "meta/llama-3.3-70b-instruct", key, question, context
    )


def _call_groq(question: str, context: str) -> tuple[str, str]:
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return None, "no key configured"
    return _call_openai_compatible(
        "Groq", "https://api.groq.com/openai/v1/chat/completions",
        "llama-3.1-8b-instant", key, question, context
    )


def _call_openrouter(question: str, context: str) -> tuple[str, str]:
    key = os.getenv("OPENROUTER_KEY", "").strip()
    if not key:
        return None, "no key configured"
    return _call_openai_compatible(
        "OpenRouter", "https://openrouter.ai/api/v1/chat/completions",
        "meta-llama/llama-3.1-8b-instruct:free", key, question, context,
        extra_headers={"HTTP-Referer": "https://dericbi-analytics.onrender.com"}
    )


def _local_fallback(question: str, df: pd.DataFrame, reason: str = "") -> str:
    """Use the local BI engine when no API key works."""
    result = generate_insight(question, df)
    if reason == "no AI API key configured":
        note = "Using the local analytics engine. Add an AI API key to unlock full AI."
    elif reason:
        note = f"Using the local analytics engine — {reason}. Try again in a moment."
    else:
        note = "Using the local analytics engine. Add an AI API key to unlock full AI."
    return result + "\n\n---\n" + note


# ── Public API ────────────────────────────────────────────────────────────────

def ask(question: str, df: "pd.DataFrame | None" = None) -> str:
    """
    Ask the AI assistant a question with optional dataset context.
    Tries APIs in order: NVIDIA → Gemini → Groq → OpenRouter → local fallback.
    If a key IS configured but the call fails, the real error is surfaced
    instead of silently pretending nothing was configured.
    """
    if not question or not question.strip():
        return "Ask me anything about your data, a business question, or how to use DericBI."

    context = build_context(df) if df is not None and not df.empty else "No dataset loaded yet."

    errors = []
    for caller in (_call_nvidia, _call_gemini, _call_groq, _call_openrouter):
        answer, error = caller(question, context)
        if answer:
            return answer
        if error and error != "no key configured":
            errors.append(error)

    if df is not None:
        reason = errors[0] if errors else "no AI API key configured"
        return _local_fallback(question, df, reason)

    if errors:
        return f"AI call failed and no data is loaded to fall back on.\n\nError: {errors[0]}"
    return "No AI API key configured and no data loaded. Upload data or add an API key."


def which_ai() -> str:
    """
    Return which AI is actually configured (has a key set).
    Does NOT guarantee the last call succeeded — see the response text
    itself for a live error if a configured key is failing.
    """
    if os.getenv("NVIDIA_API_KEY", "").strip():
        return "NVIDIA NIM Llama 3.3 70B (configured)"
    if os.getenv("GEMINI_API_KEY", "").strip():
        return "Gemini (configured)"
    if os.getenv("GROQ_API_KEY", "").strip():
        return "Groq Llama 3.1 (configured)"
    if os.getenv("OPENROUTER_KEY", "").strip():
        return "OpenRouter Llama 3.1 (configured)"
    return "Local Analytics Engine"
