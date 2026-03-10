from sklearn.linear_model import LinearRegression
import pandas as pd

def run_regression(df, x_col, y_col):
    X = df[[x_col]]
    y = df[y_col]
    model = LinearRegression()
    model.fit(X, y)
    return {
        "coef": model.coef_[0],
        "intercept": model.intercept_,
        "score": model.score(X, y)
    }
