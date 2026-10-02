import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load .env from the project root, no matter where this runs from
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not found — check your .env file")

engine = create_engine(DATABASE_URL)

def get_engine():
    """Shared engine the rest of the project imports."""
    return engine

if __name__ == "__main__":
    with engine.connect() as conn:
        db, user, ver = conn.execute(
            text("SELECT current_database(), current_user, version()")
        ).one()
    print("Connection OK")
    print(f"  database: {db}")
    print(f"  user:     {user}")
    print(f"  server:   {ver.split(',')[0]}")