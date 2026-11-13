# ============================================================
# AquaInsight — PostgreSQL Data Loader
#
# Source:
# data/processed/barentswatch_lice_pipeline_2015_2025.parquet
#
# Destination:
# aquainsight.fishhealth_weekly
#
# Features:
# - Test mode (100 records)
# - Full mode (613,601 records)
# - Source validation
# - Duplicate prevention
# - Transaction rollback
# - Import verification
# ============================================================

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.database import get_engine


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "barentswatch_lice_pipeline_2015_2025.parquet"
)

SCHEMA_NAME = "aquainsight"
TABLE_NAME = "fishhealth_weekly"

EXPECTED_ROWS = 613_601
EXPECTED_COLUMNS = 28

BATCH_SIZE = 1000

# True  = Validate import using 100 records, then roll back
# False = Import complete historical dataset
TEST_MODE = True

TEST_ROWS = 100


# ============================================================
# DATABASE ROW COUNT
# ============================================================

def get_database_count(connection):
    """
    Count records currently stored in PostgreSQL.
    """

    result = connection.execute(
        text(
            "SELECT COUNT(*) "
            "FROM aquainsight.fishhealth_weekly"
        )
    )

    return result.scalar_one()


# ============================================================
# SOURCE DATA VALIDATION
# ============================================================

def validate_source_data(df):
    """
    Verify the cleaned dataset before importing it.
    """

    print("\nValidating source dataset...")

    # Verify number of observations
    if len(df) != EXPECTED_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_ROWS:,} rows, "
            f"found {len(df):,}"
        )

    # Verify number of columns
    if len(df.columns) != EXPECTED_COLUMNS:
        raise ValueError(
            f"Expected {EXPECTED_COLUMNS} columns, "
            f"found {len(df.columns)}"
        )

    # Composite primary key
    primary_key = [
        "year",
        "week",
        "locality_id"
    ]

    # Check duplicate combinations
    duplicate_count = df.duplicated(
        subset=primary_key
    ).sum()

    if duplicate_count > 0:
        raise ValueError(
            f"Duplicate primary keys: {duplicate_count}"
        )

    # Check missing values in key columns
    missing_keys = df[primary_key].isna().sum()

    if missing_keys.sum() > 0:
        raise ValueError(
            f"Missing primary key values:\n{missing_keys}"
        )

    print("Source validation: PASSED")


# ============================================================
# LOAD PARQUET DATA
# ============================================================

def read_source_data():
    """
    Read the cleaned Parquet dataset.
    """

    if not SOURCE_FILE.is_file():
        raise FileNotFoundError(
            f"Source file not found: {SOURCE_FILE}"
        )

    df = pd.read_parquet(SOURCE_FILE)

    print("\nSource dataset loaded")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")

    validate_source_data(df)

    return df


# ============================================================
# POSTGRESQL DATA LOADER
# ============================================================

def load_postgres(test_mode=TEST_MODE):
    """
    Import cleaned BarentsWatch data into PostgreSQL.

    Test mode:
        Imports 100 rows inside a transaction.
        Verifies the import.
        Rolls back deliberately.

    Full mode:
        Imports all rows.
        Verifies the import.
        Commits the transaction.
    """

    print("\n=====================================")
    print("AquaInsight PostgreSQL Data Loader")
    print("=====================================")

    # ------------------------------------------
    # STEP 1: Read and validate source
    # ------------------------------------------

    df = read_source_data()

    # ------------------------------------------
    # STEP 2: Select import size
    # ------------------------------------------

    if test_mode:

        print("\nMODE: TEST")

        data_to_import = df.head(
            TEST_ROWS
        ).copy()

    else:

        print("\nMODE: FULL IMPORT")

        data_to_import = df.copy()

    print(
        f"Records selected: {len(data_to_import):,}"
    )

    # ------------------------------------------
    # STEP 3: Create database connection
    # ------------------------------------------

    engine = get_engine()

    try:

        # Explicit transaction: commit only after
        # all checks pass in full-import mode.
        with engine.connect() as connection:

            transaction = connection.begin()

            try:

                # ----------------------------------
                # STEP 4: Check existing records
                # ----------------------------------

                existing_count = get_database_count(
                    connection
                )

                print(
                    f"Existing PostgreSQL records: "
                    f"{existing_count:,}"
                )

                if existing_count != 0:
                    raise RuntimeError(
                        "Destination table is not empty. "
                        "Import stopped to prevent duplicates."
                    )

                # ----------------------------------
                # STEP 5: Insert records
                # ----------------------------------

                print("\nImporting records...")

                data_to_import.to_sql(
                    name=TABLE_NAME,
                    con=connection,
                    schema=SCHEMA_NAME,
                    if_exists="append",
                    index=False,
                    chunksize=BATCH_SIZE,
                    method=None,
                )

                # ----------------------------------
                # STEP 6: Verify imported row count
                # ----------------------------------

                imported_count = get_database_count(
                    connection
                )

                expected_count = len(
                    data_to_import
                )

                if imported_count != expected_count:
                    raise AssertionError(
                        f"Import verification failed. "
                        f"Expected {expected_count:,}, "
                        f"found {imported_count:,}"
                    )

                print(
                    f"Verified imported records: "
                    f"{imported_count:,}"
                )

                # ----------------------------------
                # STEP 7: Commit or roll back
                # ----------------------------------

                if test_mode:

                    # Test successful, but do not
                    # permanently save test records.
                    transaction.rollback()

                    print(
                        "\nTEST PASSED: "
                        "100 records inserted and verified."
                    )

                    print(
                        "Transaction rolled back. "
                        "Database remains unchanged."
                    )

                else:

                    transaction.commit()

                    print(
                        "\nFULL IMPORT COMPLETED!"
                    )

                    print(
                        f"Successfully stored "
                        f"{imported_count:,} records."
                    )

            except Exception:

                if transaction.is_active:
                    transaction.rollback()

                print(
                    "\nIMPORT FAILED. "
                    "Transaction rolled back."
                )

                raise

    finally:

        engine.dispose()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    load_postgres(test_mode=TEST_MODE)
