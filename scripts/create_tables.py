"""Create the GridSense tables in Neon. Safe to run more than once."""
import os
from pathlib import Path
import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL is missing. Put it in your .env file.")

sql = (Path(__file__).parent.parent / "sql" / "001_create_tables.sql").read_text()

with psycopg.connect(url) as conn:
    conn.execute(sql)
    print("Tables created (or already there):")
    for (name,) in conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' ORDER BY table_name"
    ):
        print(" -", name)