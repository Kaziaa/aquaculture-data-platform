"""
AquaInsight — Incremental PostgreSQL Loader

Stage 15: Transaction-Safe Incremental Ingestion

Purpose:
    Load validated fish-health observations into PostgreSQL
    using parameterized UPSERT statements.

Features:
    - Strict input validation
    - Parameterized PostgreSQL UPSERT
    - Multi-batch processing
    - INSERT, UPDATE, and SKIP classification
    - NULL-safe change detection
    - Transaction management
    - Automatic rollback on failure

Safety:
    - Only the approved temporary PostgreSQL table is permitted.
    - Production-table writes are disabled.
    - The transactional entry point uses one transaction.
    - Failed transactions are rolled back automatically.

Compatibility:
    PostgreSQL 16+
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.incremental_fishhealth import prepare_database_records
from src.incremental_upsert import build_upsert_statement
from src.incremental_metrics import classify_incremental_records


# ============================================================
# STEP 1: CONFIGURATION
# ============================================================

DEFAULT_BATCH_SIZE = 500

TEMPORARY_TABLE_NAME = "fishhealth_upsert_test"

PRODUCTION_TARGET = (
    '"aquainsight"."fishhealth_weekly"'
)

TEMPORARY_TARGET = (
    '"pg_temp"."fishhealth_upsert_test"'
)


# ============================================================
# STEP 2: VALIDATE BATCH SIZE
# ============================================================

def validate_batch_size(batch_size: int) -> None:
    """
    Ensure that batch_size is a positive integer.

    Boolean values are rejected because Python treats
    bool as a subclass of int.
    """

    if (
        not isinstance(batch_size, int)
        or isinstance(batch_size, bool)
        or batch_size <= 0
    ):
        raise ValueError(
            "batch_size must be a positive integer"
        )


# ============================================================
# STEP 3: BUILD TEMPORARY-TABLE UPSERT
# ============================================================

def build_temporary_upsert():
    """
    Generate the parameterized UPSERT statement.

    Redirect the predefined production SQL target to
    the approved PostgreSQL temporary table.

    No SQL is executed by this function.
    """

    original_sql = str(build_upsert_statement())

    # The expected production target must occur once.
    if original_sql.count(PRODUCTION_TARGET) != 1:

        raise RuntimeError(
            "Unexpected production table reference "
            "in generated UPSERT statement"
        )

    # Redirect to the temporary table.
    temporary_sql = original_sql.replace(
        PRODUCTION_TARGET,
        TEMPORARY_TARGET,
        1,
    )

    # Verify the production target is absent.
    if PRODUCTION_TARGET in temporary_sql:

        raise RuntimeError(
            "Production table reference remains "
            "after SQL redirection"
        )

    return text(temporary_sql)


# ============================================================
# STEP 4: INCREMENTAL BATCH LOADER
# ============================================================

def load_incremental_data(
    df,
    connection: Connection,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    target_table: str = TEMPORARY_TABLE_NAME,
) -> dict:
    """
    Incrementally load observations into a temporary table.

    Parameters
    ----------
    df:
        Incoming cleaned fish-health DataFrame.

    connection:
        Active SQLAlchemy PostgreSQL connection.

    batch_size:
        Number of observations processed per batch.

    target_table:
        Approved PostgreSQL temporary table name.

    Returns
    -------
    dict:
        input_records
        inserted_records
        updated_records
        unchanged_records
        affected_records

    Important
    ---------
    This function does not commit or roll back.

    The caller controls transaction management.

    The INSERT and UPDATE classifications are obtained
    immediately before the UPSERT operation.

    Classification is intended for isolated testing.
    It is not concurrency-safe for production ingestion.
    """

    # --------------------------------------------------------
    # STEP 4.1: Validate batch size
    # --------------------------------------------------------

    validate_batch_size(batch_size)

    # --------------------------------------------------------
    # STEP 4.2: Restrict destination table
    # --------------------------------------------------------

    if target_table != TEMPORARY_TABLE_NAME:

        raise ValueError(
            "Only the approved temporary test table "
            "is permitted"
        )

    # --------------------------------------------------------
    # STEP 4.3: Prepare database-ready records
    # --------------------------------------------------------

    records = prepare_database_records(df)

    total_records = len(records)

    # --------------------------------------------------------
    # STEP 4.4: Build parameterized UPSERT
    # --------------------------------------------------------

    statement = build_temporary_upsert()

    # --------------------------------------------------------
    # STEP 4.5: Initialize ingestion metrics
    # --------------------------------------------------------

    inserted_records = 0

    updated_records = 0

    unchanged_records = 0

    affected_records = 0

    # --------------------------------------------------------
    # STEP 4.6: Process incoming records in batches
    # --------------------------------------------------------

    for start in range(0, total_records, batch_size):

        batch = records[
            start:start + batch_size
        ]

        # ----------------------------------------------------
        # A. Classify this batch before executing its UPSERT
        # ----------------------------------------------------

        batch_metrics = classify_incremental_records(
            batch,
            connection,
        )

        expected_inserted = (
            batch_metrics["inserted_records"]
        )

        expected_updated = (
            batch_metrics["updated_records"]
        )

        expected_unchanged = (
            batch_metrics["unchanged_records"]
        )

        expected_affected = (
            expected_inserted + expected_updated
        )

        # ----------------------------------------------------
        # B. Execute the actual PostgreSQL UPSERT
        # ----------------------------------------------------

        result = connection.execute(
            statement,
            batch,
        )

        actual_affected = result.rowcount

        # ----------------------------------------------------
        # C. Verify affected-record count
        # ----------------------------------------------------

        if actual_affected != expected_affected:

            raise RuntimeError(
                "Ingestion metrics mismatch.\n"
                f"Expected affected: {expected_affected}\n"
                f"Actual affected: {actual_affected}\n"
                "The transaction should be rolled back."
            )

        # ----------------------------------------------------
        # D. Accumulate batch metrics
        # ----------------------------------------------------

        inserted_records += expected_inserted

        updated_records += expected_updated

        unchanged_records += expected_unchanged

        affected_records += actual_affected

    # --------------------------------------------------------
    # STEP 4.7: Verify final metrics
    # --------------------------------------------------------

    if (
        inserted_records
        + updated_records
        + unchanged_records
        != total_records
    ):

        raise AssertionError(
            "Ingestion classification totals "
            "do not match input records"
        )

    if (
        inserted_records + updated_records
        != affected_records
    ):

        raise AssertionError(
            "Affected record count does not match "
            "INSERT and UPDATE classifications"
        )

    # --------------------------------------------------------
    # STEP 4.8: Build ingestion summary
    # --------------------------------------------------------

    summary = {
        "input_records": total_records,
        "inserted_records": inserted_records,
        "updated_records": updated_records,
        "unchanged_records": unchanged_records,
        "affected_records": affected_records,
    }

    # --------------------------------------------------------
    # STEP 4.9: Display results
    # --------------------------------------------------------

    print("\nAquaInsight — Incremental Ingestion Summary")

    print(
        f"Input records: {total_records:,}"
    )

    print(
        f"Inserted records: {inserted_records:,}"
    )

    print(
        f"Updated records: {updated_records:,}"
    )

    print(
        f"Unchanged records: {unchanged_records:,}"
    )

    print(
        f"Total affected records: {affected_records:,}"
    )

    print(
        "PASS: Incremental ingestion completed"
    )

    return summary


# ============================================================
# STEP 5: TRANSACTION-SAFE INCREMENTAL LOADER
# ============================================================

def load_incremental_transactional(
    df,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    engine=None,
) -> dict:
    """
    Execute incremental ingestion inside one transaction.

    Workflow:
        1. Validate batch size.
        2. Open a database transaction.
        3. Create an isolated temporary table.
        4. Validate incoming observations.
        5. Classify and execute UPSERT batches.
        6. Commit on success.
        7. Roll back automatically on failure.

    The temporary table uses ON COMMIT DROP.

    Production records are never targeted.
    """

    # --------------------------------------------------------
    # STEP 5.1: Require explicit database engine
    # --------------------------------------------------------

    if engine is None:

        raise ValueError(
            "An explicit database engine is required"
        )

    # --------------------------------------------------------
    # STEP 5.2: Validate batch size
    # --------------------------------------------------------

    validate_batch_size(batch_size)

    # --------------------------------------------------------
    # STEP 5.3: Execute within one transaction
    # --------------------------------------------------------

    with engine.begin() as connection:

        # ----------------------------------------------------
        # A. Create isolated temporary PostgreSQL table
        # ----------------------------------------------------

        connection.execute(text("""
            CREATE TEMP TABLE fishhealth_upsert_test
            (
                LIKE aquainsight.fishhealth_weekly
                INCLUDING ALL
            )
            ON COMMIT DROP
        """))

        # ----------------------------------------------------
        # B. Execute incremental ingestion
        # ----------------------------------------------------

        summary = load_incremental_data(
            df,
            connection,
            batch_size=batch_size,
        )

    # --------------------------------------------------------
    # STEP 5.4: Transaction completed
    # --------------------------------------------------------

    # SQLAlchemy automatically commits after successful
    # execution of the engine.begin() block.
    #
    # If an exception occurs inside the block,
    # SQLAlchemy automatically rolls back.
    #
    # ON COMMIT DROP removes the temporary table.

    print(
        "PASS: Transaction committed successfully"
    )

    return summary
