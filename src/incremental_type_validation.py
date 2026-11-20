"""
AquaInsight — Strict Incremental Data Type Validation

Purpose:
    Validate incoming values against the PostgreSQL
    fishhealth_weekly column types.

Safety:
    - No database connection
    - No file modifications
    - No automatic conversion of invalid strings
"""

import math
import numbers

import numpy as np
import pandas as pd


# ============================================================
# DATABASE COLUMN TYPE CONTRACT
# ============================================================

INTEGER_COLUMNS = [
    "year",
    "week",
    "locality_id",
    "municipality_id",
    "county_id",
    "production_area_id",
]

FLOAT_COLUMNS = [
    "adult_female_lice",
    "mobile_lice",
    "attached_lice",
    "latitude",
    "longitude",
    "weekly_lice_limit",
    "sea_temperature",
    "sea_temperature_clean",
]

BOOLEAN_COLUMNS = [
    "probably_without_fish",
    "lice_counted",
    "over_lice_limit",
    "reporting_conflict",
    "temperature_outlier",
    "adult_female_lice_extreme",
    "mobile_lice_extreme",
    "attached_lice_extreme",
    "calculated_lice_exceedance",
]

TEXT_COLUMNS = [
    "locality_name",
    "municipality",
    "county",
    "production_area",
    "weekly_lice_limit_original",
]

PRIMARY_KEY = [
    "year",
    "week",
    "locality_id",
]

ALL_COLUMNS = (
    INTEGER_COLUMNS
    + FLOAT_COLUMNS
    + BOOLEAN_COLUMNS
    + TEXT_COLUMNS
)

BIGINT_MIN = -(2**63)
BIGINT_MAX = 2**63 - 1


# ============================================================
# INDIVIDUAL VALUE VALIDATION
# ============================================================

def is_valid_integer(value):
    """
    Accept integer values that fit PostgreSQL BIGINT.

    Reject Booleans, strings, infinity, and fractions.
    """

    if isinstance(value, (bool, np.bool_)):
        return False

    if isinstance(value, numbers.Integral):
        return BIGINT_MIN <= int(value) <= BIGINT_MAX

    if isinstance(value, numbers.Real):

        if not math.isfinite(value):
            return False

        if not float(value).is_integer():
            return False

        return BIGINT_MIN <= value < 2**63

    return False


def is_valid_float(value):
    """
    Accept finite real numbers.

    Reject Boolean values and numeric strings.
    """

    if isinstance(value, (bool, np.bool_)):
        return False

    if not isinstance(value, numbers.Real):
        return False

    return math.isfinite(value)


def is_valid_boolean(value):
    """
    Accept only actual Boolean values.
    """

    return isinstance(
        value,
        (bool, np.bool_),
    )


def is_valid_text(value):
    """
    Accept only strings.
    """

    return isinstance(value, str)


# ============================================================
# COMPLETE DATAFRAME TYPE VALIDATION
# ============================================================

def validate_column_types(
    df: pd.DataFrame,
) -> None:
    """
    Validate every value against its expected
    PostgreSQL column type.

    Missing values are allowed only for
    non-primary-key columns.

    Raises ValueError for invalid values.
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a DataFrame")

    if not df.columns.is_unique:
        raise ValueError("Duplicate column names")

    if len(ALL_COLUMNS) != 28:
        raise AssertionError(
            "Column contract must contain 28 columns"
        )

    if len(set(ALL_COLUMNS)) != 28:
        raise AssertionError(
            "Duplicate columns in type contract"
        )

    if set(df.columns) != set(ALL_COLUMNS):
        raise ValueError(
            "Input columns do not match type contract"
        )

    validators = {}

    for column in INTEGER_COLUMNS:
        validators[column] = is_valid_integer

    for column in FLOAT_COLUMNS:
        validators[column] = is_valid_float

    for column in BOOLEAN_COLUMNS:
        validators[column] = is_valid_boolean

    for column in TEXT_COLUMNS:
        validators[column] = is_valid_text

    # Validate all incoming values.
    for column in df.columns:

        validator = validators[column]

        for row_position, value in enumerate(
            df[column].array
        ):

            # Missing values are allowed for
            # non-primary-key columns.
            if pd.isna(value):

                if column in PRIMARY_KEY:
                    raise ValueError(
                        f"Missing primary key: {column}, "
                        f"row {row_position}"
                    )

                continue

            if not validator(value):
                raise ValueError(
                    f"Invalid value in column '{column}', "
                    f"row {row_position}: {value!r}"
                )

    print(
        "PASS: All 28 column types validated"
    )
