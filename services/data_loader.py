import pandas as pd
import sqlalchemy

def load_csv(file_path):
    return pd.read_csv(file_path)

def load_excel(file_path):
    return pd.read_excel(file_path)

def load_sql(connection_string, query):
    engine = sqlalchemy.create_engine(connection_string)
    return pd.read_sql(query, engine)
