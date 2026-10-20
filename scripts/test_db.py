"""Check that you can connect to your Neon Postgres database."""
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL is missing. Put it in your .env file.")

with psycopg.connect(url) as conn:
    version = conn.execute("SELECT version();").fetchone()[0]
    print("Connected!")
    print(version)