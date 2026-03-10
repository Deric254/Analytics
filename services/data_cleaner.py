import pandas as pd

def handle_missing(df, strategy="drop"):
    if strategy == "drop":
        return df.dropna()
    elif strategy == "mean":
        return df.fillna(df.mean())
    elif strategy == "median":
        return df.fillna(df.median())
    return df

def remove_duplicates(df):
    return df.drop_duplicates()

def remove_outliers(df, threshold=3):
    df_copy = df.copy()
    for col in df_copy.select_dtypes(include="number").columns:
        z_scores = (df_copy[col] - df_copy[col].mean()) / df_copy[col].std()
        df_copy = df_copy[(z_scores.abs() < threshold)]
    return df_copy
