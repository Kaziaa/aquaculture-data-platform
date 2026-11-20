"""
AquaInsight — PostgreSQL Incremental Ingestion Metrics

Stage 15: Test record classification.

Purpose:
    Classify incoming observations as INSERT, UPDATE,
    or SKIP before executing PostgreSQL upserts.

Safety:
    - Uses a PostgreSQL temporary table
    - No production-table writes
    - Transaction rolled back after testing
"""

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.database import get_engine
from src.incremental_fishhealth import (
    prepare_database_records,
    UPDATE_COLUMNS,
)


def test_incremental_record_classification():

    # --------------------------------------------------------
    # STEP 1: Load three valid observations
    # --------------------------------------------------------

    project_root = Path(__file__).resolve().parents[1]

    source = (
        project_root
        / "tests"
        / "fixtures"
        / "fishhealth_sample.parquet"
    )

    df = pd.read_parquet(source).head(3).copy()

    records = prepare_database_records(df)

    for index, record in enumerate(records):
        record["year"] = 2099
        record["week"] = 1
        record["locality_id"] = 987690001 + index

    # --------------------------------------------------------
    # STEP 2: Build comparison SQL
    # --------------------------------------------------------

    existing_values = ", ".join(
        f't."{column}"'
        for column in UPDATE_COLUMNS
    )

    incoming_values = ", ".join(
        f':{column}'
        for column in UPDATE_COLUMNS
    )

    classification_sql = text(f"""
        SELECT
            CASE
                WHEN t.locality_id IS NULL
                    THEN 'INSERT'

                WHEN ({existing_values})
                     IS DISTINCT FROM
                     ({incoming_values})
                    THEN 'UPDATE'

                ELSE 'SKIP'
            END AS operation

        FROM (SELECT 1) AS dummy

        LEFT JOIN pg_temp.fishhealth_metrics_test AS t

            ON t.year = :year
            AND t.week = :week
            AND t.locality_id = :locality_id
    """)

    # --------------------------------------------------------
    # STEP 3: Create isolated temporary table
    # --------------------------------------------------------

    engine = get_engine()

    try:
        with engine.connect() as connection:

            transaction = connection.begin()

            try:

                connection.execute(text("""
                    CREATE TEMP TABLE fishhealth_metrics_test
                    (
                        LIKE aquainsight.fishhealth_weekly
                        INCLUDING ALL
                    )
                    ON COMMIT DROP
                """))

                print("PASS: Temporary table created")

                # --------------------------------------------
                # TEST 1: New observation
                # --------------------------------------------

                operation = connection.execute(
                    classification_sql,
                    records[0],
                ).scalar_one()

                assert operation == "INSERT"

                print("PASS: New observation classified as INSERT")

                # --------------------------------------------
                # TEST 2: Existing unchanged observation
                # --------------------------------------------

                # Insert one record into the temporary table.
                from src.incremental_upsert import (
                    build_upsert_statement,
                )

                sql = str(build_upsert_statement())

                sql = sql.replace(
                    '"aquainsight"."fishhealth_weekly"',
                    '"pg_temp"."fishhealth_metrics_test"',
                    1,
                )

                connection.execute(
                    text(sql),
                    records[0],
                )

                operation = connection.execute(
                    classification_sql,
                    records[0],
                ).scalar_one()

                assert operation == "SKIP"

                print("PASS: Identical observation classified as SKIP")

                # --------------------------------------------
                # TEST 3: Existing corrected observation
                # --------------------------------------------

                corrected = records[0].copy()

                corrected["adult_female_lice"] = 9.99

                operation = connection.execute(
                    classification_sql,
                    corrected,
                ).scalar_one()

                assert operation == "UPDATE"

                print("PASS: Corrected observation classified as UPDATE")

                # --------------------------------------------
                # TEST 4: NULL-safe comparison
                # --------------------------------------------

                corrected["adult_female_lice"] = None

                operation = connection.execute(
                    classification_sql,
                    corrected,
                ).scalar_one()

                assert operation == "UPDATE"

                print("PASS: NULL change classified as UPDATE")

            finally:
                transaction.rollback()

    finally:
        engine.dispose()

    print("PASS: All ingestion classifications verified")
    print("Production database modifications: NONE")
