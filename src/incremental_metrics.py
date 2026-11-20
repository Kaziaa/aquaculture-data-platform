"""
AquaInsight — Incremental Ingestion Metrics

Purpose:
    Classify incoming observations as:
        INSERT
        UPDATE
        SKIP

Compatibility:
    PostgreSQL 16+

Safety:
    Classification is read-only.
    Only the approved temporary table is queried.
"""

from collections import Counter

from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.incremental_fishhealth import (
    PRIMARY_KEY,
    UPDATE_COLUMNS,
)


TEMPORARY_TABLE = "pg_temp.fishhealth_upsert_test"


def build_classification_statement():
    """
    Generate a parameterized SQL query that classifies
    an incoming observation.

    Returns
    -------
    sqlalchemy.sql.elements.TextClause
    """

    existing_values = ", ".join(
        f't."{column}"'
        for column in UPDATE_COLUMNS
    )

    incoming_values = ", ".join(
        f':{column}'
        for column in UPDATE_COLUMNS
    )

    sql = f"""
        SELECT
            CASE
                WHEN t."locality_id" IS NULL
                    THEN 'INSERT'

                WHEN ({existing_values})
                     IS DISTINCT FROM
                     ({incoming_values})
                    THEN 'UPDATE'

                ELSE 'SKIP'
            END AS operation

        FROM (SELECT 1) AS source

        LEFT JOIN {TEMPORARY_TABLE} AS t

            ON t."year" = :year
            AND t."week" = :week
            AND t."locality_id" = :locality_id
    """

    return text(sql)


def classify_incremental_records(
    records: list[dict],
    connection: Connection,
) -> dict:
    """
    Classify incoming database-ready records.

    Parameters
    ----------
    records:
        Validated Python dictionaries.

    connection:
        Active SQLAlchemy connection containing
        the approved temporary table.

    Returns
    -------
    dict:
        inserted_records
        updated_records
        unchanged_records

    Important:
        This function only classifies records.
        It does not insert or update them.
    """

    if not records:
        raise ValueError(
            "No records supplied for classification"
        )

    statement = build_classification_statement()

    counts = Counter()

    for record in records:

        operation = connection.execute(
            statement,
            record,
        ).scalar_one()

        if operation not in {"INSERT", "UPDATE", "SKIP"}:
            raise RuntimeError(
                f"Unexpected ingestion operation: {operation}"
            )

        counts[operation] += 1

    summary = {
        "inserted_records": counts["INSERT"],
        "updated_records": counts["UPDATE"],
        "unchanged_records": counts["SKIP"],
    }

    assert sum(summary.values()) == len(records)

    return summary
