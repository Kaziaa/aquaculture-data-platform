"""
AquaInsight — Incremental PostgreSQL Upsert Integration Test

Tests:
    - Insert a new observation
    - Update an existing observation
    - Skip an identical observation
    - Update a measurement to NULL
    - Prevent duplicate primary keys

Safety:
    Uses a temporary PostgreSQL table.
    Does not modify production records.
"""

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.database import get_engine
from src.incremental_fishhealth import prepare_database_records
from src.incremental_upsert import build_upsert_statement


def test_incremental_upsert():

    # --------------------------------------------------------
    # STEP 1: Prepare a valid observation
    # --------------------------------------------------------

    project_root = Path(__file__).resolve().parents[1]

    source = (
        project_root
        / "tests"
        / "fixtures"
        / "fishhealth_sample.parquet"
    )

    df = pd.read_parquet(source).head(1).copy()

    record = prepare_database_records(df)[0]

    # Use a test-only primary key.
    record["year"] = 2099
    record["week"] = 1
    record["locality_id"] = 987654321
    record["adult_female_lice"] = 0.2

    # --------------------------------------------------------
    # STEP 2: Redirect SQL to the temporary table
    # --------------------------------------------------------

    original_sql = str(build_upsert_statement())

    production_target = '"aquainsight"."fishhealth_weekly"'
    temporary_target = '"pg_temp"."fishhealth_upsert_test"'

    assert original_sql.count(production_target) == 1

    test_sql = original_sql.replace(
        production_target,
        temporary_target,
        1,
    )

    assert production_target not in test_sql

    upsert = text(test_sql)

    # --------------------------------------------------------
    # STEP 3: Connect to PostgreSQL
    # --------------------------------------------------------

    engine = get_engine()

    try:
        with engine.connect() as connection:

            transaction = connection.begin()

            try:
                # --------------------------------------------
                # Create isolated temporary table
                # --------------------------------------------

                connection.execute(text("""
                    CREATE TEMP TABLE fishhealth_upsert_test
                    (
                        LIKE aquainsight.fishhealth_weekly
                        INCLUDING ALL
                    )
                    ON COMMIT DROP
                """))

                print("PASS: Temporary table created")

                # --------------------------------------------
                # TEST 1: INSERT
                # --------------------------------------------

                result = connection.execute(
                    upsert,
                    record,
                )

                assert result.rowcount == 1

                print("PASS: New observation inserted")

                # --------------------------------------------
                # TEST 2: UPDATE
                # --------------------------------------------

                updated_record = record.copy()
                updated_record["adult_female_lice"] = 0.5

                result = connection.execute(
                    upsert,
                    updated_record,
                )

                assert result.rowcount == 1

                value = connection.execute(text("""
                    SELECT adult_female_lice
                    FROM pg_temp.fishhealth_upsert_test
                """)).scalar_one()

                assert value == 0.5

                print("PASS: Changed observation updated")

                # --------------------------------------------
                # TEST 3: SKIP UNCHANGED RECORD
                # --------------------------------------------

                result = connection.execute(
                    upsert,
                    updated_record,
                )

                assert result.rowcount == 0

                print("PASS: Identical observation skipped")

                # --------------------------------------------
                # TEST 4: UPDATE TO NULL
                # --------------------------------------------

                null_record = updated_record.copy()
                null_record["adult_female_lice"] = None

                result = connection.execute(
                    upsert,
                    null_record,
                )

                assert result.rowcount == 1

                value = connection.execute(text("""
                    SELECT adult_female_lice
                    FROM pg_temp.fishhealth_upsert_test
                """)).scalar_one()

                assert value is None

                print("PASS: Measurement updated to NULL")

                # --------------------------------------------
                # TEST 5: VERIFY NO DUPLICATES
                # --------------------------------------------

                count = connection.execute(text("""
                    SELECT COUNT(*)
                    FROM pg_temp.fishhealth_upsert_test
                """)).scalar_one()

                assert count == 1

                print("PASS: No duplicate records")

            finally:
                transaction.rollback()

    finally:
        engine.dispose()

    print("PASS: PostgreSQL integration test completed")
# ============================================================
# TEST 2: MULTI-RECORD UPSERT
# ============================================================

def test_multi_record_upsert():
    """
    Verify batch insertion, idempotency, and selective updates.

    Uses an isolated PostgreSQL temporary table.
    """

    project_root = Path(__file__).resolve().parents[1]

    source = (
        project_root
        / "tests"
        / "fixtures"
        / "fishhealth_sample.parquet"
    )

    # Prepare five real observations.
    df = pd.read_parquet(source).head(5).copy()

    records = prepare_database_records(df)

    # Assign test-only primary keys.
    for index, record in enumerate(records):
        record["year"] = 2099
        record["week"] = 1
        record["locality_id"] = 987654321 + index

    # Redirect SQL to our temporary table.
    original_sql = str(build_upsert_statement())

    production_target = '"aquainsight"."fishhealth_weekly"'
    temporary_target = '"pg_temp"."fishhealth_upsert_test"'

    assert original_sql.count(production_target) == 1

    test_sql = original_sql.replace(
        production_target,
        temporary_target,
        1,
    )

    upsert = text(test_sql)

    engine = get_engine()

    try:
        with engine.connect() as connection:

            transaction = connection.begin()

            try:
                # Create isolated test table.
                connection.execute(text("""
                    CREATE TEMP TABLE fishhealth_upsert_test
                    (
                        LIKE aquainsight.fishhealth_weekly
                        INCLUDING ALL
                    )
                    ON COMMIT DROP
                """))

                # --------------------------------------------
                # TEST A: Insert five observations
                # --------------------------------------------

                result = connection.execute(
                    upsert,
                    records,
                )

                assert result.rowcount == 5

                count = connection.execute(text("""
                    SELECT COUNT(*)
                    FROM pg_temp.fishhealth_upsert_test
                """)).scalar_one()

                assert count == 5

                print("PASS: Five observations inserted")

                # --------------------------------------------
                # TEST B: Reprocess identical observations
                # --------------------------------------------

                result = connection.execute(
                    upsert,
                    records,
                )

                assert result.rowcount == 0

                print("PASS: Five unchanged observations skipped")

                # --------------------------------------------
                # TEST C: Update one observation
                # --------------------------------------------

                updated_records = [
                    record.copy()
                    for record in records
                ]

                updated_records[0]["adult_female_lice"] = 9.99

                result = connection.execute(
                    upsert,
                    updated_records,
                )

                assert result.rowcount == 1

                print("PASS: Only one changed observation updated")

                # --------------------------------------------
                # TEST D: Verify unchanged records
                # --------------------------------------------

                rows = connection.execute(text("""
                    SELECT locality_id, adult_female_lice
                    FROM pg_temp.fishhealth_upsert_test
                    ORDER BY locality_id
                """)).all()

                assert len(rows) == 5
                assert rows[0][1] == 9.99

                for index in range(1, 5):
                    assert (
                        rows[index][1]
                        == records[index]["adult_female_lice"]
                    )

                print("PASS: Other four observations unchanged")

            finally:
                transaction.rollback()

    finally:
        engine.dispose()

    print("PASS: Multi-record upsert test completed")
# ============================================================
# TEST 3: TRANSACTION ROLLBACK AFTER FAILURE
# ============================================================

def test_transaction_rollback_on_batch_failure():
    """
    Verify that a failed ingestion transaction does not
    leave partially inserted observations.

    Uses an isolated PostgreSQL temporary table.
    """

    from sqlalchemy.exc import DBAPIError

    project_root = Path(__file__).resolve().parents[1]

    source = (
        project_root
        / "tests"
        / "fixtures"
        / "fishhealth_sample.parquet"
    )

    df = pd.read_parquet(source).head(2).copy()

    records = prepare_database_records(df)

    # Assign isolated test-only primary keys.
    for index, record in enumerate(records):
        record["year"] = 2099
        record["week"] = 1
        record["locality_id"] = 987650001 + index

    # Build SQL targeting a temporary PostgreSQL table.
    original_sql = str(build_upsert_statement())

    production_target = '"aquainsight"."fishhealth_weekly"'
    temporary_target = '"pg_temp"."fishhealth_upsert_test"'

    assert original_sql.count(production_target) == 1

    test_sql = original_sql.replace(
        production_target,
        temporary_target,
        1,
    )

    upsert = text(test_sql)

    engine = get_engine()

    try:
        with engine.connect() as connection:

            # Create the temporary table in its own transaction.
            # ON COMMIT PRESERVE ROWS keeps it available
            # for verification after rollback.
            connection.execute(text("""
                CREATE TEMP TABLE fishhealth_upsert_test
                (
                    LIKE aquainsight.fishhealth_weekly
                    INCLUDING ALL
                )
                ON COMMIT PRESERVE ROWS
            """))

            connection.commit()

            # ------------------------------------------------
            # STEP 1: Start ingestion transaction
            # ------------------------------------------------

            transaction = connection.begin()

            try:

                # Insert a valid observation.
                connection.execute(
                    upsert,
                    records[0],
                )

                print("PASS: First observation inserted")

                # Create deliberately invalid second record.
                invalid_record = records[1].copy()

                # A primary-key column cannot be NULL.
                invalid_record["locality_id"] = None

                # Attempt invalid insertion.
                connection.execute(
                    upsert,
                    invalid_record,
                )

                raise AssertionError(
                    "FAIL: Invalid observation was accepted"
                )

            except DBAPIError:

                print("PASS: PostgreSQL rejected invalid observation")

                transaction.rollback()

                print("PASS: Transaction rolled back")

            else:

                transaction.commit()

                raise AssertionError(
                    "FAIL: Transaction unexpectedly succeeded"
                )

            # ------------------------------------------------
            # STEP 2: Verify rollback
            # ------------------------------------------------

            count = connection.execute(text("""
                SELECT COUNT(*)
                FROM pg_temp.fishhealth_upsert_test
            """)).scalar_one()

            assert count == 0, (
                f"Rollback failed: {count} records remain"
            )

            print("PASS: No partially inserted records remain")

            connection.rollback()

    finally:
        engine.dispose()

    print("PASS: Transaction rollback test completed")
