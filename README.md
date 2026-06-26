# DericBI Analytics Engine

**Professional local analytics platform — no API keys, no subscriptions, no cloud required.**

Built on Python + Dash + Plotly. Runs entirely on your machine.

---

## Quick Start

### 1. Requirements
- Python 3.10 or newer
- pip

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run
```bash
python run.py
```

Open your browser at: **http://127.0.0.1:10000**

---

## Run options

```bash
python run.py                    # default: port 10000
python run.py --port 8050        # custom port
python run.py --debug            # hot-reload for development
python run.py --install          # force re-install requirements first
```

---

## Features

| Page | What it does |
|------|-------------|
| **Ingestion** | Upload CSV / Excel, or connect to MySQL / PostgreSQL |
| **Cleaning** | Handle missing values, duplicates, outliers, type conversion, row filters |
| **Exploration** | Aggregate, slice, rank, and push results to Visualization |
| **Visualization** | Bar, line, scatter, histogram, box, violin, pie, pareto, heatmap. KPI builder. Export HTML/PDF/ZIP |
| **Insights** | Fully local AI-style analytics engine — no API key needed |
| **Reporting** | Auto-generated dataset report, export as HTML or PDF |

---

## Insights Engine (no API key needed)

The Insights page uses a local analytics engine that understands natural language keywords
and routes them to the right analysis:

| You ask about... | Engine runs... |
|-----------------|----------------|
| overview, summary | Data quality + numeric stats + correlations |
| quality, missing, duplicates | Per-column missing counts, duplicate rows |
| correlations, relationships | Pearson r matrix, all pairs above threshold |
| outliers, anomalies | IQR method per column, exact ranges |
| trends, growth | Date-aware trend, earliest vs latest quarter |
| distribution, spread | Skewness, kurtosis, percentiles |
| top, best, worst, rank | Top/bottom N by column, grouped |
| compare, versus, by | Sum/mean/count of numeric by categorical |
| categories, breakdown | Value counts with percentages |

Use the **quick-action buttons** or type any question freely.

---

## Database connection

The Ingestion page supports direct SQL connections:
- **MySQL** — provide host, port, user, password, database
- **PostgreSQL / Neon** — same, or paste a full connection string
- SSL supported for cloud databases

Only SELECT queries are permitted for safety.

---

## Project structure

```
DericBI/
├── run.py                  ← START HERE
├── app.py                  ← Dash app definition
├── requirements.txt
├── assets/
│   ├── dericbi.css
│   └── zzz_dropdown_final.css
├── config/
│   ├── settings.py
│   └── theme.py
├── pages/
│   ├── ingestion.py
│   ├── cleaning.py
│   ├── exploration.py
│   ├── visualization.py
│   ├── insights.py         ← rebuilt: local engine
│   └── reporting.py
├── services/
│   ├── insights_agent.py   ← rebuilt: zero API keys
│   ├── export_utils.py
│   ├── report_generator.py
│   └── ...
└── components/
    ├── chart_card.py
    ├── kpi_card.py
    └── ...
```

---

## Contact

- Website: https://dericbi.vercel.app  
- Email: dericmarangu@gmail.com  
- WhatsApp: +254 791 360 805
