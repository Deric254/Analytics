import os

# ── Branding ──────────────────────────────────────────────────────────────────
DERICBI_LOGO   = "https://dericbi.vercel.app/assets/img/logo.png"
DERICBI_SLOGAN = "Cut Through Noise"
DERICBI_CONTACT = {
    "website":  "https://dericbi.vercel.app",
    "email":    "dericmarangu@gmail.com",
    "whatsapp": "+254791360805",
}

# ── Optional: database connection string (not required for file uploads) ──────
DB_CONNECTION_STRING = os.getenv(
    "DB_CONNECTION_STRING",
    "postgresql://user:password@localhost:5432/dericbi_db",
)
