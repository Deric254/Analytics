import os

# DericBI Settings Configuration

# HuggingFace API key loaded from environment.
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "google/flan-t5-large")

# Database connection string (example for PostgreSQL)
DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING", "postgresql://user:password@localhost:5432/dericbi_db")

# Branding constants
DERICBI_LOGO = "https://dericbi.vercel.app/assets/img/logo.png"
DERICBI_SLOGAN = "Cut Through Noise"
DERICBI_CONTACT = {
    "website": "https://dericbi.vercel.app",
    "email": "dericmarangu@gmail.com",
    "whatsapp": "+254791360805"
}
