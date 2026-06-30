"""
Built-in sample dataset — loads automatically on first visit.
Gives the system something to show immediately.
Realistic business data: wire manufacturing sales (fits IMARA LINKS context).
"""
import pandas as pd
import numpy as np
import json


def get_sample_dataset() -> dict:
    """Return a realistic sample dataset as a shared-dataset store dict."""
    np.random.seed(42)
    n = 240  # 8 months of daily records

    dates     = pd.date_range("2024-01-01", periods=n, freq="D")
    regions   = np.random.choice(["Nairobi", "Mombasa", "Kisumu", "Nakuru"], n,
                                  p=[0.40, 0.25, 0.20, 0.15])
    products  = np.random.choice(["Wire 2mm", "Wire 3mm", "Wire 4mm", "Wire 6mm"], n,
                                  p=[0.35, 0.30, 0.25, 0.10])
    customers = np.random.choice(
        ["Buildmart", "SteelCo", "IronTech", "MetalWorks", "ConstructPro"], n,
        p=[0.30, 0.25, 0.20, 0.15, 0.10],
    )

    # Revenue with trend + seasonality
    base_rev  = 85_000
    trend     = np.linspace(0, 20_000, n)
    seasonal  = 12_000 * np.sin(np.linspace(0, 4 * np.pi, n))
    noise     = np.random.normal(0, 8_000, n)
    revenue   = (base_rev + trend + seasonal + noise).clip(20_000).round(2)

    # Cost ~55% of revenue + noise
    cost      = (revenue * np.random.uniform(0.50, 0.62, n)).round(2)
    quantity  = np.random.randint(50, 600, n)

    # Inject a few missing values and one outlier
    revenue[15] = np.nan
    revenue[73] = np.nan
    revenue[120] = 380_000   # outlier

    df = pd.DataFrame({
        "Date":     dates.strftime("%Y-%m-%d"),
        "Region":   regions,
        "Product":  products,
        "Customer": customers,
        "Revenue":  revenue,
        "Cost":     cost,
        "Quantity": quantity,
    })

    return {
        "filename": "sample_data.csv  (built-in demo — replace via Ingestion)",
        "records":  df.to_dict("records"),
        "is_sample": True,
    }
