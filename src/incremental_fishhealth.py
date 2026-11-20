"""
AquaInsight — Incremental Fish Health Ingestion

Stage 15: Input Validation

Purpose:
    Validate incoming cleaned BarentsWatch observations
    before incremental PostgreSQL ingestion.

Features:
    - Validate the 28-column database schema
    - Accept columns in any order
    - Reject missing or unexpected columns
    - Reject duplicate column names
    - Validate primary-key values
    - Reject missing primary keys
    - Reject duplicate primary keys
    - Validate year and week ranges
    - Return an independent DataFrame copy

Safety:
    - Does not modify the original DataFrame
    - Does not connect to PostgreSQL
    - Does not insert, update, or delete records
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.incremental_type_validation import validate_column_types


# ============================================================
# STEP 1: PRIMARY KEY CONFIGURATION
# ============================================================

PRIMARY_KEY = [
    "year",
    "week",
    "locality_id",
]


# ============================================================
# STEP 2: EXPECTED DATABASE SCHEMA
# ============================================================

EXPECTED_COLUMNS = [
    "year",
    "week",
    "locality_id",
    "locality_name",
    "adult_female_lice",
    "mobile_lice",
    "attached_lice",
    "probably_without_fish",
    "lice_counted",
    "municipality_id",
    "municipality",
    "county_id",
    "county",
    "latitude",
    "longitude",
    "weekly_lice_limit",
    "over_lice_limit",
    "sea_temperature",
    "production_area_id",
    "production_area",
    "weekly_lice_limit_original",
    "reporting_conflict",
    "temperature_outlier",
    "sea_temperature_clean",
    "adult_female_lice_extreme",
    "mobile_lice_extreme",
    "attached_lice_extreme",
    "calculated_lice_exceedance",
]


# ============================================================
# STEP 3: UPDATABLE DATABASE COLUMNS
# ============================================================

UPDATE_COLUMNS = [
    column
    for column in EXPECTED_COLUMNS
    if column not in PRIMARY_KEY
]


# ============================================================
# STEP 4: PRIMARY-KEY VALUE VALIDATION
# ============================================================

def validate_integer_column(
    values: pd.Series,
    column_name: str,
) -> None:
    """
    Validate integer-valued primary-key columns.

    Accepts:
        - Python integers
        - NumPy integers
        - Integer-valued finite floating-point numbers

    Rejects:
        - Boolean values
        - Strings
        - Missing values
        - Infinite values
        - Decimal values

    Does not modify the input Series.
    """

    # --------------------------------------------------------
    # A. Reject missing values
    # --------------------------------------------------------

    if values.isna().any():

        raise ValueError(
            f"Primary key '{column_name}' "
            "contains missing values"
        )

    # --------------------------------------------------------
    # B. Reject Boolean data
    # --------------------------------------------------------

    if pd.api.types.is_bool_dtype(values):

        raise ValueError(
            f"Primary key '{column_name}' "
            "cannot contain Boolean values"
        )

    # --------------------------------------------------------
    # C. Validate individual values
    # --------------------------------------------------------

    for value in values:

        # Reject Boolean scalar values.
        if isinstance(
            value,
            (bool, np.bool_),
        ):

            raise ValueError(
                f"Primary key '{column_name}' "
                "contains a Boolean value"
            )

        # Accept integer values.
        if isinstance(
            value,
            (int, np.integer),
        ):

            continue

        # Accept finite integer-valued floats.
        if isinstance(
            value,
            (float, np.floating),
        ):

            if (
                not np.isfinite(value)
                or not float(value).is_integer()
            ):

                raise ValueError(
                    f"Primary key '{column_name}' "
                    "must contain finite integers"
                )

            continue

        # Reject strings and unsupported types.
        raise ValueError(
            f"Primary key '{column_name}' "
            f"contains unsupported value: {value!r}"
        )


# ============================================================
# STEP 5: INCREMENTAL DATA VALIDATION
# ============================================================

def validate_incremental_data(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Validate incoming cleaned fish-health observations.

    Parameters
    ----------
    df : pandas.DataFrame
        Incoming observations.

    Returns
    -------
    pandas.DataFrame
        Validated independent copy of the input.

        Columns are arranged according to EXPECTED_COLUMNS.

    Raises
    ------
    TypeError
        If the input is not a pandas DataFrame.

    ValueError
        If the dataset contains invalid columns,
        missing primary keys, invalid key values,
        or duplicate primary keys.
    """

    # --------------------------------------------------------
    # STEP 5.1: Validate input type
    # --------------------------------------------------------

    if not isinstance(df, pd.DataFrame):

        raise TypeError(
            "Input must be a pandas DataFrame"
        )

    # --------------------------------------------------------
    # STEP 5.2: Reject empty datasets
    # --------------------------------------------------------

    if df.empty:

        raise ValueError(
            "Incremental dataset cannot be empty"
        )

    # --------------------------------------------------------
    # STEP 5.3: Reject duplicate column names
    # --------------------------------------------------------

    if not df.columns.is_unique:

        raise ValueError(
            "Duplicate column names detected"
        )

    # --------------------------------------------------------
    # STEP 5.4: Validate column names
    # --------------------------------------------------------

    actual_columns = list(df.columns)

    missing_columns = [
        column
        for column in EXPECTED_COLUMNS
        if column not in actual_columns
    ]

    unexpected_columns = [
        column
        for column in actual_columns
        if column not in EXPECTED_COLUMNS
    ]

    if missing_columns or unexpected_columns:

        raise ValueError(
            "Invalid incremental dataset schema.\n"
            f"Missing columns: {missing_columns}\n"
            f"Unexpected columns: {unexpected_columns}"
        )

    # --------------------------------------------------------
    # STEP 5.5: Create independent, ordered copy
    # --------------------------------------------------------

    validated = df.loc[
        :,
        EXPECTED_COLUMNS
    ].copy(deep=True)

    # --------------------------------------------------------
    # STEP 5.6: Check missing primary keys
    # --------------------------------------------------------

    missing_keys = (
        validated[PRIMARY_KEY]
        .isna()
        .any(axis=1)
    )

    if missing_keys.any():

        raise ValueError(
            "Missing primary-key values detected: "
            f"{int(missing_keys.sum())} rows"
        )

    # --------------------------------------------------------
    # STEP 5.7: Validate primary-key types
    # --------------------------------------------------------

    for column in PRIMARY_KEY:

        validate_integer_column(
            validated[column],
            column,
        )

    # --------------------------------------------------------
    # STEP 5.8: Validate reporting years
    # --------------------------------------------------------

    if not validated["year"].between(
        2015,
        2100,
    ).all():

        raise ValueError(
            "Year must be between 2015 and 2100"
        )

    # --------------------------------------------------------
    # STEP 5.9: Validate reporting weeks
    # --------------------------------------------------------

    if not validated["week"].between(
        1,
        53,
    ).all():

        raise ValueError(
            "Week must be between 1 and 53"
        )

    # --------------------------------------------------------
    # STEP 5.10: Validate locality identifiers
    # --------------------------------------------------------

    if not (
        validated["locality_id"] > 0
    ).all():

        raise ValueError(
            "Locality ID must be positive"
        )

    # --------------------------------------------------------
    # STEP 5.11: Reject duplicate primary keys
    # --------------------------------------------------------

    duplicate_keys = validated.duplicated(
        subset=PRIMARY_KEY,
        keep=False,
    )

    if duplicate_keys.any():

        raise ValueError(
            "Duplicate primary keys detected: "
            f"{int(duplicate_keys.sum())} rows"
        )

    # --------------------------------------------------------
    # STEP 5.12: Validate schema configuration
    # --------------------------------------------------------

    if len(EXPECTED_COLUMNS) != 28:

        raise AssertionError(
            "Expected exactly 28 database columns"
        )

    if len(PRIMARY_KEY) != 3:

        raise AssertionError(
            "Expected exactly 3 primary-key columns"
        )

    if len(UPDATE_COLUMNS) != 25:

        raise AssertionError(
            "Expected exactly 25 updatable columns"
        )

    # --------------------------------------------------------
    # STEP 5.13: Display validation summary
    # --------------------------------------------------------

    print(
        "PASS: Incremental data validation completed"
    )

    print(
        f"Validated records: {len(validated):,}"
    )

    print(
        f"Primary-key columns: {len(PRIMARY_KEY)}"
    )

    print(
        f"Updatable columns: {len(UPDATE_COLUMNS)}"
    )

    return validated

# ============================================================
# STEP 6: CONVERT VALIDATED DATA INTO DATABASE RECORDS
# ============================================================

def prepare_database_records(
    df: pd.DataFrame,
) -> list[dict]:
    """
    Validate incoming observations and convert them into
    Python dictionaries suitable for parameterized SQL.

    Missing values become None, allowing database drivers
    to translate them into SQL NULL.

    No database connection is created.
    """

    # STEP 1: Validate incoming data
    validated = validate_incremental_data(df)

    # STEP 2: Validate all 28 PostgreSQL column types
    validate_column_types(validated)

    # STEP 3: Reject infinity in numeric columns
    numeric_columns = validated.select_dtypes(
        include=["number"]
    ).columns

    for column in numeric_columns:

        values = validated[column].dropna()

        if not np.isfinite(
            values.to_numpy(dtype="float64")
        ).all():

            raise ValueError(
                f"Non-finite numeric values detected in {column}"
            )

    # STEP 3: Convert pandas missing values to None
    converted = validated.astype(object).where(
        pd.notna(validated),
        None,
    )

    # STEP 4: Convert DataFrame to dictionaries
    records = converted.to_dict(
        orient="records"
    )

    # STEP 5: Verify output structure
    if len(records) != len(validated):

        raise AssertionError(
            "Record conversion changed the observation count"
        )

    if not all(
        set(record) == set(EXPECTED_COLUMNS)
        for record in records
    ):

        raise AssertionError(
            "Record conversion produced an unexpected schema"
        )

    print(
        f"PASS: Prepared {len(records):,} database records"
    )

    return records
