"""
AquaInsight — Reusable Ingestion Metrics Integration Test

Purpose:
    Test INSERT, UPDATE, and SKIP classification
    against PostgreSQL 16.

Safety:
    Uses an isolated temporary table.
    All test writes are rolled back.
"""

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.database import get_engine
from src.incremental_fishhealth import prepare_database_records
from src.incremental_metrics import classify_incremental_records
from src.incremental_upsert import build_upsert_statement


def test_classify_incremental_records():

    # ========================================================
    # STEP 1: PREPARE THREE OBSERVATIONS
    # ========================================================

    project_root = Path(__file__).resolve().parents[1]

    source = (
        project_root
        / "tests"
        / "fixtures"
        / "fishhealth_sample.parquet"
    )

    df = pd.read_parquet(source).head(3).copy()

    records = prepare_database_records(df)

    # Assign test-only primary keys.
    for index, record in enumerate(records):
        record["year"] = 2099
        record["week"] = 1
        record["locality_id"] = 987700001 + index

    # ========================================================
    # STEP 2: PREPARE TEMPORARY-TABLE UPSERT
    # ========================================================

    production_target = '"aquainsight"."fishhealth_weekly"'
    temporary_target = '"pg_temp"."fishhealth_upsert_test"'

    original_sql = str(build_upsert_statement())

    assert original_sql.count(production_target) == 1

    upsert = text(
        original_sql.replace(
            production_target,
            temporary_target,
            1,
        )
    )

    # ========================================================
    # STEP 3: CREATE TEMPORARY TABLE
    # ========================================================

    engine = get_engine()

    try:
        with engine.connect() as connection:

            transaction = connection.begin()

            try:
                connection.execute(text("""
                    CREATE TEMP TABLE fishhealth_upsert_test
                    (
                        LIKE aquainsight.fishhealth_weekly
                        INCLUDING ALL
                    )
                    ON COMMIT DROP
                """))

                # =================================================
                # TEST 1: CLASSIFY NEW RECORDS
                # =================================================

                initial = classify_incremental_records(
                    records,
                    connection,
                )

                assert initial == {
                    "inserted_records": 3,
                    "updated_records": 0,
                    "unchanged_records": 0,
                }

                print("PASS: Three new records classified as INSERT")

                # =================================================
                # TEST 2: INSERT TWO RECORDS
                # =================================================

                connection.execute(
                    upsert,
                    records[:2],
                )

                # One new record remains.
                mixed = classify_incremental_records(
                    records,
                    connection,
                )

                assert mixed == {
                    "inserted_records": 1,
                    "updated_records": 0,
                    "unchanged_records": 2,
                }

                print("PASS: New and unchanged records classified")

                # =================================================
                # TEST 3: CORRECT ONE MEASUREMENT
                # =================================================

                corrected = [
                    record.copy()
                    for record in records
                ]

                corrected[0]["adult_female_lice"] = 9.99

                updated = classify_incremental_records(
                    corrected,
                    connection,
                )

                assert updated == {
                    "inserted_records": 1,
                    "updated_records": 1,
                    "unchanged_records": 1,
                }

                print("PASS: Corrected record classified as UPDATE")

                # =================================================
                # TEST 4: DETECT CHANGE TO NULL
                # =================================================

                corrected[0]["adult_female_lice"] = None

                null_update = classify_incremental_records(
                    corrected,
                    connection,
                )

                assert null_update == {
                    "inserted_records": 1,
                    "updated_records": 1,
                    "unchanged_records": 1,
                }

                print("PASS: Change to NULL classified as UPDATE")

            finally:
                transaction.rollback()

    finally:
        engine.dispose()

    print("PASS: Reusable ingestion metrics verified")
    print("Production database modifications: NONE")
