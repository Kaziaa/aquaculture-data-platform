# ============================================================
# AquaInsight — PostgreSQL Database Connection
# Day 8 — Shared SQLAlchemy Engine
# ============================================================

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")


# ============================================================
# DATABASE ENGINE
# ============================================================

@lru_cache(maxsize=1)
def get_engine():
    """
    Create and cache one SQLAlchemy Engine per Python process.

    Repeated calls return the same Engine instance.
    """

    password = os.getenv("DB_PASSWORD")

    if not password:
        raise ValueError(
            "DB_PASSWORD is missing from the .env file"
        )

    database_url = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("DB_USER"),
        password=password,
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME"),
    )

    return create_engine(
        database_url,
        pool_pre_ping=True
    )


# ============================================================
# DATABASE CONNECTION TEST
# ============================================================

def test_connection():
    """
    Verify that Python can connect to PostgreSQL.
    """

    engine = get_engine()

    with engine.connect() as connection:

        result = connection.execute(
            text("SELECT current_database(), current_user")
        )

        database, user = result.one()

        print("Database:", database)
        print("Connected user:", user)
        print("PostgreSQL connection: SUCCESS")


# ============================================================
# RETRIEVE AVAILABLE REPORTING YEARS
# ============================================================

def get_available_years():
    """
    Retrieve reporting years available in PostgreSQL.

    Returns:
        A sorted list of integers.
    """

    engine = get_engine()

    query = text("""
        SELECT DISTINCT year
        FROM aquainsight.fishhealth_weekly
        ORDER BY year
    """)

    with engine.connect() as connection:

        result = connection.execute(query)

        years = result.scalars().all()

    return list(years)

if __name__ == "__main__":
    test_connection()
