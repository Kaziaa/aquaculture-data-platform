"""
AquaInsight — Incremental Loader Transaction Tests

Purpose:
    Verify that a failure in a later ingestion batch
    does not leave partially committed observations.

Safety:
    - Uses a PostgreSQL temporary table.
    - Never writes to the production fishhealth table.
    - Rolls back the ingestion transaction.
"""

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.database import get_engine
from src.incremental_loader import load_incremental_data


def test_multi_batch_failure_rolls_back():
    """
    Simulate a failure during the second batch.

    Verify that the first batch is also rolled back.
    """

    # ========================================================
    # STEP 1: PREPARE SIX OBSERVATIONS
    # ========================================================

    project_root = Path(__file__).resolve().parents[1]

    source = (
        project_root
        / "tests"
        / "fixtures"
        / "fishhealth_sample.parquet"
    )

    df = pd.read_parquet(source).head(6).copy()

    # Use unique test-only primary keys.
    df["year"] = 2099
    df["week"] = 1
    df["locality_id"] = range(
        987660001,
        987660007,
    )

    # ========================================================
    # STEP 2: CONNECT AND CREATE TEMPORARY TABLE
    # ========================================================

    engine = get_engine()

    try:
        with engine.connect() as connection:

            connection.execute(text("""
                CREATE TEMP TABLE fishhealth_upsert_test
                (
                    LIKE aquainsight.fishhealth_weekly
                    INCLUDING ALL
                )
                ON COMMIT PRESERVE ROWS
            """))

            # Commit only the temporary table creation.
            # This keeps the table available after rollback.
            connection.commit()

            # =================================================
            # STEP 3: SIMULATE FAILURE IN SECOND BATCH
            # =================================================

            original_execute = Connection.execute

            batch_calls = 0

            def simulated_execute(
                self,
                statement,
                parameters=None,
                *args,
                **kwargs,
            ):
                nonlocal batch_calls

                # Identify the actual upsert statement.
                if (
                    "INSERT INTO" in str(statement)
                    and "fishhealth_upsert_test" in str(statement)
                ):
                    batch_calls += 1

                    if batch_calls == 2:
                        raise RuntimeError(
                            "Simulated second-batch failure"
                        )

                return original_execute(
                    self,
                    statement,
                    parameters,
                    *args,
                    **kwargs,
                )

            transaction = connection.begin()

            try:

                with patch.object(
                    Connection,
                    "execute",
                    simulated_execute,
                ):

                    with pytest.raises(
                        RuntimeError,
                        match="Simulated second-batch failure",
                    ):

                        load_incremental_data(
                            df,
                            connection,
                            batch_size=3,
                        )

                assert batch_calls == 2

                print(
                    "PASS: Second-batch failure detected"
                )

            finally:

                transaction.rollback()

                print(
                    "PASS: Ingestion transaction rolled back"
                )

            # =================================================
            # STEP 4: VERIFY NO PARTIAL DATA REMAINS
            # =================================================

            remaining = connection.execute(text("""
                SELECT COUNT(*)
                FROM pg_temp.fishhealth_upsert_test
            """)).scalar_one()

            assert remaining == 0, (
                f"Rollback failed: {remaining} rows remain"
            )

            print(
                "PASS: No partial records remain"
            )

            connection.rollback()

    finally:
        engine.dispose()

    print(
        "PASS: Multi-batch rollback test completed"
    )
# ============================================================
# TEST 2: AUTOMATIC TRANSACTION ROLLBACK
# ============================================================

def test_transactional_loader_automatic_rollback():
    """
    Verify that the transactional loader automatically
    rolls back when a later batch fails.

    All writes target an isolated temporary table.
    """

    from src.incremental_loader import load_incremental_transactional

    project_root = Path(__file__).resolve().parents[1]

    source = (
        project_root
        / "tests"
        / "fixtures"
        / "fishhealth_sample.parquet"
    )

    df = pd.read_parquet(source).head(6).copy()

    # Assign test-only primary keys.
    df["year"] = 2099
    df["week"] = 1
    df["locality_id"] = range(
        987680001,
        987680007,
    )

    engine = get_engine()

    # Record the production-table row count before testing.
    # This works with both local and CI databases.
    with engine.connect() as connection:
        count_before = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM aquainsight.fishhealth_weekly
            """)
        ).scalar_one()

    original_execute = Connection.execute
    batch_calls = 0

    def simulated_execute(
        self,
        statement,
        parameters=None,
        *args,
        **kwargs,
    ):
        nonlocal batch_calls

        if (
            "INSERT INTO" in str(statement)
            and "fishhealth_upsert_test" in str(statement)
        ):
            batch_calls += 1

            if batch_calls == 2:
                raise RuntimeError(
                    "Simulated transactional batch failure"
                )

        return original_execute(
            self,
            statement,
            parameters,
            *args,
            **kwargs,
        )

    try:

        with patch.object(
            Connection,
            "execute",
            simulated_execute,
        ):

            with pytest.raises(
                RuntimeError,
                match="Simulated transactional batch failure",
            ):

                load_incremental_transactional(
                    df,
                    batch_size=3,
                    engine=engine,
                )

        assert batch_calls == 2

        print("PASS: Second-batch failure detected")

        # The transaction must have rolled back.
        # CREATE TEMP TABLE was inside that transaction,
        # so the temporary table should no longer exist.

        with engine.connect() as connection:

            table_exists = connection.execute(text("""
                SELECT to_regclass(
                    'pg_temp.fishhealth_upsert_test'
                )
            """)).scalar_one()

            assert table_exists is None

        print("PASS: Failed transaction rolled back")
        print("PASS: Temporary table creation rolled back")

        # Verify the production table's row count.
        with engine.connect() as connection:

            count = connection.execute(text("""
                SELECT COUNT(*)
                FROM aquainsight.fishhealth_weekly
            """)).scalar_one()

            assert count == count_before

        print("PASS: Production row count unchanged")

    finally:
        engine.dispose()

    print("PASS: Automatic rollback test completed")
def test_integrated_ingestion_metrics():
    """
    Verify INSERT, UPDATE, and SKIP metrics.

    Uses an isolated PostgreSQL temporary table.
    All database changes are rolled back.
    """

    from pathlib import Path

    import pandas as pd
    from sqlalchemy import text

    from src.database import get_engine
    from src.incremental_loader import load_incremental_data

    # STEP 1: Prepare test observations

    project_root = Path(__file__).resolve().parents[1]

    source = (
        project_root
        / "tests"
        / "fixtures"
        / "fishhealth_sample.parquet"
    )

    df = pd.read_parquet(source).head(5).copy()

    df["year"] = 2099
    df["week"] = 1
    df["locality_id"] = range(987720001, 987720006)

    engine = get_engine()

    try:
        with engine.connect() as connection:

            transaction = connection.begin()

            try:
                # STEP 2: Create temporary test table

                connection.execute(text("""
                    CREATE TEMP TABLE fishhealth_upsert_test
                    (
                        LIKE aquainsight.fishhealth_weekly
                        INCLUDING ALL
                    )
                    ON COMMIT DROP
                """))

                # STEP 3: First ingestion — five INSERTs

                first = load_incremental_data(
                    df,
                    connection,
                    batch_size=2,
                )

                assert first == {
                    "input_records": 5,
                    "inserted_records": 5,
                    "updated_records": 0,
                    "unchanged_records": 0,
                    "affected_records": 5,
                }

                print("PASS: INSERT metrics verified")

                # STEP 4: Identical re-ingestion — five SKIPs

                second = load_incremental_data(
                    df,
                    connection,
                    batch_size=2,
                )

                assert second == {
                    "input_records": 5,
                    "inserted_records": 0,
                    "updated_records": 0,
                    "unchanged_records": 5,
                    "affected_records": 0,
                }

                print("PASS: SKIP metrics verified")

                # STEP 5: Modify one measurement — one UPDATE

                corrected = df.copy()

                corrected.loc[
                    corrected.index[0],
                    "adult_female_lice",
                ] = 9.99

                third = load_incremental_data(
                    corrected,
                    connection,
                    batch_size=2,
                )

                assert third == {
                    "input_records": 5,
                    "inserted_records": 0,
                    "updated_records": 1,
                    "unchanged_records": 4,
                    "affected_records": 1,
                }

                print("PASS: UPDATE metrics verified")

                # STEP 6: Verify actual PostgreSQL values

                actual = connection.execute(text("""
                    SELECT adult_female_lice
                    FROM pg_temp.fishhealth_upsert_test
                    WHERE year = 2099
                      AND week = 1
                      AND locality_id = 987720001
                """)).scalar_one()

                assert actual == 9.99

                count = connection.execute(text("""
                    SELECT COUNT(*)
                    FROM pg_temp.fishhealth_upsert_test
                """)).scalar_one()

                assert count == 5

                print("PASS: PostgreSQL records verified")

            finally:
                transaction.rollback()

    finally:
        engine.dispose()

    print("PASS: Integrated ingestion metrics regression test")
