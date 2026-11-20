"""
AquaInsight — PostgreSQL Incremental Upsert

Purpose:
    Generate a parameterized PostgreSQL upsert statement.

Features:
    - Insert new records
    - Update changed records
    - Skip unchanged records
    - Compare NULL values correctly
    - Preserve primary-key columns

Safety:
    This module only generates SQL.
    It does not connect to PostgreSQL.
"""

from sqlalchemy import text

from src.incremental_fishhealth import (
    EXPECTED_COLUMNS,
    PRIMARY_KEY,
    UPDATE_COLUMNS,
)


SCHEMA_NAME = "aquainsight"
TABLE_NAME = "fishhealth_weekly"


def build_upsert_statement():
    """
    Build a PostgreSQL INSERT ... ON CONFLICT statement.

    Returns
    -------
    sqlalchemy.sql.elements.TextClause
        Parameterized SQL statement.
    """

    # --------------------------------------------------------
    # STEP 1: Validate column configuration
    # --------------------------------------------------------

    if len(EXPECTED_COLUMNS) != 28:
        raise ValueError("Expected 28 database columns")

    if len(PRIMARY_KEY) != 3:
        raise ValueError("Expected 3 primary-key columns")

    if len(UPDATE_COLUMNS) != 25:
        raise ValueError("Expected 25 updatable columns")

    # --------------------------------------------------------
    # STEP 2: Construct INSERT columns
    # --------------------------------------------------------

    insert_columns = ", ".join(
        f'"{column}"'
        for column in EXPECTED_COLUMNS
    )

    # Named parameters prevent values from being
    # interpolated directly into SQL.
    insert_values = ", ".join(
        f":{column}"
        for column in EXPECTED_COLUMNS
    )

    # --------------------------------------------------------
    # STEP 3: Construct conflict target
    # --------------------------------------------------------

    conflict_columns = ", ".join(
        f'"{column}"'
        for column in PRIMARY_KEY
    )

    # --------------------------------------------------------
    # STEP 4: Construct UPDATE assignments
    # --------------------------------------------------------

    update_assignments = ",\n        ".join(
        f'"{column}" = EXCLUDED."{column}"'
        for column in UPDATE_COLUMNS
    )

    # --------------------------------------------------------
    # STEP 5: Compare all updatable columns
    # --------------------------------------------------------

    # PostgreSQL row comparison with IS DISTINCT FROM
    # handles NULL values correctly.

    existing_values = ", ".join(
        f'target."{column}"'
        for column in UPDATE_COLUMNS
    )

    incoming_values = ", ".join(
        f'EXCLUDED."{column}"'
        for column in UPDATE_COLUMNS
    )

    # --------------------------------------------------------
    # STEP 6: Build complete upsert statement
    # --------------------------------------------------------

    sql = f"""
    INSERT INTO "{SCHEMA_NAME}"."{TABLE_NAME}" AS target
        ({insert_columns})
    VALUES
        ({insert_values})

    ON CONFLICT ({conflict_columns})

    DO UPDATE SET
        {update_assignments}

    WHERE
        ({existing_values})
        IS DISTINCT FROM
        ({incoming_values})
    """

    return text(sql)
