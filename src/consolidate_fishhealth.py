"""
AquaInsight — Historical CSV Consolidation

Purpose:
    Combine BarentsWatch annual CSV files (2015–2025)
    into one validated Parquet dataset.

Features:
    - Validate all 11 historical CSV files
    - Validate consistent column schemas
    - Validate reporting years
    - Detect missing primary keys
    - Detect duplicate primary keys
    - Preserve original regulatory thresholds
    - Convert thresholds to numeric values
    - Validate expected row and column counts
    - Compare against existing reference Parquet
    - Save a separate rebuilt Parquet file

IMPORTANT:
    The original historical Parquet file is never overwritten.
"""

from pathlib import Path

import pandas as pd


# ============================================================
# STEP 1: PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_ROOT / "data" / "raw"

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

REFERENCE_FILE = (
    PROCESSED_DIR
    / "barentswatch_lice_2015_2025.parquet"
)

OUTPUT_FILE = (
    PROCESSED_DIR
    / "barentswatch_lice_2015_2025_rebuilt.parquet"
)

EXPECTED_YEARS = range(2015, 2026)

EXPECTED_ROWS = 613_601

EXPECTED_COLUMNS = 21

EXPECTED_MISSING_THRESHOLDS = 127

PRIMARY_KEY = [
    "Lokalitetsnummer",
    "År",
    "Uke",
]


# ============================================================
# STEP 2: DISCOVER HISTORICAL CSV FILES
# ============================================================

def discover_files():
    """
    Find all expected annual CSV files.

    Each year from 2015 to 2025 must have a source file.
    """

    print("\nSTEP 1: Discovering source files")

    csv_files = []

    for year in EXPECTED_YEARS:

        file = (
            RAW_DIR
            / f"barentswatch_lice_{year}.csv"
        )

        if not file.is_file():

            raise FileNotFoundError(
                f"Missing source file: {file}"
            )

        csv_files.append(file)

        print(f"PASS: {file.name}")

    print(f"\nTotal files: {len(csv_files)}")

    return csv_files


# ============================================================
# STEP 3: VALIDATE CSV COLUMN SCHEMAS
# ============================================================

def validate_schemas(csv_files):
    """
    Ensure every annual CSV contains the same columns
    in the same order.
    """

    print("\nSTEP 2: Validating CSV schemas")

    reference_columns = pd.read_csv(
        csv_files[0],
        nrows=0
    ).columns.tolist()

    if len(reference_columns) != 20:

        raise ValueError(
            "Expected 20 columns in raw CSV files, "
            f"found {len(reference_columns)}"
        )

    for file in csv_files:

        columns = pd.read_csv(
            file,
            nrows=0
        ).columns.tolist()

        if columns != reference_columns:

            raise ValueError(
                f"Schema mismatch in {file.name}\n"
                f"Expected: {reference_columns}\n"
                f"Found: {columns}"
            )

        print(f"PASS: {file.name}")

    # Verify that the columns needed for validation exist
    required_columns = set(PRIMARY_KEY) | {
        "Lusegrense uke"
    }

    missing_columns = (
        required_columns - set(reference_columns)
    )

    if missing_columns:

        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    print(
        f"\nValidated columns: {len(reference_columns)}"
    )


# ============================================================
# STEP 4: LOAD AND VALIDATE ANNUAL CSV FILES
# ============================================================

def load_annual_data(csv_files):
    """
    Load annual datasets and validate:
        - Reporting years
        - Missing primary keys
        - Duplicate primary keys
    """

    print("\nSTEP 3: Loading annual CSV files")

    dataframes = []

    for file in csv_files:

        year = int(
            file.stem.split("_")[-1]
        )

        df = pd.read_csv(
            file,
            low_memory=False
        )

        # ----------------------------------------------------
        # Check for empty datasets
        # ----------------------------------------------------

        if df.empty:

            raise ValueError(
                f"Empty dataset: {file.name}"
            )

        # ----------------------------------------------------
        # Verify reporting year
        # ----------------------------------------------------

        if not df["År"].eq(year).all():

            raise ValueError(
                f"Incorrect reporting year in {file.name}"
            )

        # ----------------------------------------------------
        # Check missing primary-key values
        # ----------------------------------------------------

        missing_keys = (
            df[PRIMARY_KEY].isna().sum()
        )

        if missing_keys.sum() > 0:

            raise ValueError(
                f"Missing primary keys in {file.name}\n"
                f"{missing_keys}"
            )

        # ----------------------------------------------------
        # Check duplicate primary keys
        # ----------------------------------------------------

        duplicate_count = df.duplicated(
            subset=PRIMARY_KEY
        ).sum()

        if duplicate_count > 0:

            raise ValueError(
                f"{duplicate_count} duplicate primary keys "
                f"in {file.name}"
            )

        dataframes.append(df)

        print(
            f"PASS: {year} | {len(df):,} rows"
        )

    return dataframes


# ============================================================
# STEP 5: CONSOLIDATE ANNUAL DATASETS
# ============================================================

def consolidate_data(dataframes):
    """
    Combine the annual DataFrames and reproduce the
    original notebook's regulatory-threshold conversion.

    Original notebook:
        01_data_validation.ipynb
        Cells 10, 15, and 18.
    """

    print("\nSTEP 4: Consolidating datasets")

    # --------------------------------------------------------
    # A. Combine annual datasets vertically
    # --------------------------------------------------------

    combined = pd.concat(
        dataframes,
        axis=0,
        ignore_index=True
    )

    # --------------------------------------------------------
    # B. Preserve original regulatory threshold values
    # --------------------------------------------------------

    # The original values may include numeric thresholds
    # and nonnumeric values such as "Ukjent".

    combined["Lusegrense_original"] = (
        combined["Lusegrense uke"]
    )

    # --------------------------------------------------------
    # C. Convert regulatory threshold to numeric
    # --------------------------------------------------------

    # errors="coerce" converts nonnumeric values to NaN.
    #
    # This is necessary for numerical comparisons.

    combined["Lusegrense uke"] = pd.to_numeric(
        combined["Lusegrense uke"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # D. Convert original thresholds to pandas string dtype
    # --------------------------------------------------------

    # Preserve original values for audit and
    # data-quality analysis.

    combined["Lusegrense_original"] = (
        combined["Lusegrense_original"].astype("string")
    )

    # --------------------------------------------------------
    # E. Validate missing regulatory thresholds
    # --------------------------------------------------------

    missing_thresholds = int(
        combined["Lusegrense uke"].isna().sum()
    )

    if missing_thresholds != EXPECTED_MISSING_THRESHOLDS:

        raise ValueError(
            "Unexpected missing regulatory thresholds. "
            f"Expected {EXPECTED_MISSING_THRESHOLDS}, "
            f"found {missing_thresholds}"
        )

    print(
        f"Missing regulatory thresholds: "
        f"{missing_thresholds:,}"
    )

    # --------------------------------------------------------
    # F. Display consolidated dataset dimensions
    # --------------------------------------------------------

    print(
        f"Combined observations: {len(combined):,}"
    )

    print(
        f"Combined columns: {len(combined.columns)}"
    )

    return combined


# ============================================================
# STEP 6: VALIDATE CONSOLIDATED DATA
# ============================================================

def validate_combined_data(df):
    """
    Validate the consolidated historical dataset.
    """

    print("\nSTEP 5: Validating consolidated data")

    # --------------------------------------------------------
    # Validate row count
    # --------------------------------------------------------

    if len(df) != EXPECTED_ROWS:

        raise ValueError(
            f"Expected {EXPECTED_ROWS:,} rows, "
            f"found {len(df):,}"
        )

    print("PASS: Expected row count")

    # --------------------------------------------------------
    # Validate column count
    # --------------------------------------------------------

    if len(df.columns) != EXPECTED_COLUMNS:

        raise ValueError(
            f"Expected {EXPECTED_COLUMNS} columns, "
            f"found {len(df.columns)}"
        )

    print("PASS: Expected column count")

    # --------------------------------------------------------
    # Validate missing primary keys
    # --------------------------------------------------------

    if df[PRIMARY_KEY].isna().any().any():

        raise ValueError(
            "Combined dataset contains missing primary keys"
        )

    print("PASS: No missing primary keys")

    # --------------------------------------------------------
    # Validate duplicate primary keys
    # --------------------------------------------------------

    duplicate_count = df.duplicated(
        subset=PRIMARY_KEY
    ).sum()

    if duplicate_count > 0:

        raise ValueError(
            f"Combined dataset contains "
            f"{duplicate_count} duplicate primary keys"
        )

    print("PASS: No duplicate primary keys")

    # --------------------------------------------------------
    # Validate reporting years
    # --------------------------------------------------------

    actual_years = set(
        df["År"].unique()
    )

    if actual_years != set(EXPECTED_YEARS):

        raise ValueError(
            f"Unexpected reporting years: {actual_years}"
        )

    print("PASS: All reporting years present")

    # --------------------------------------------------------
    # Validate preserved threshold column
    # --------------------------------------------------------

    if "Lusegrense_original" not in df.columns:

        raise ValueError(
            "Original regulatory threshold column missing"
        )

    if not pd.api.types.is_numeric_dtype(
        df["Lusegrense uke"]
    ):

        raise TypeError(
            "Lusegrense uke must be numeric"
        )

    print("PASS: Regulatory threshold conversion")


# ============================================================
# STEP 7: COMPARE AGAINST ORIGINAL PARQUET
# ============================================================

def compare_reference(df):
    """
    Compare the rebuilt dataset with the original
    notebook-generated Parquet file.

    The comparison checks:
        - Row count
        - Column count and order
        - Data types
        - Cell values
        - Missing values
    """

    print("\nSTEP 6: Comparing reference dataset")

    if not REFERENCE_FILE.is_file():

        raise FileNotFoundError(
            f"Reference dataset missing: {REFERENCE_FILE}"
        )

    reference = pd.read_parquet(
        REFERENCE_FILE
    )

    print(
        f"Original dataset: "
        f"{len(reference):,} rows × "
        f"{len(reference.columns)} columns"
    )

    print(
        f"Rebuilt dataset: "
        f"{len(df):,} rows × "
        f"{len(df.columns)} columns"
    )

    pd.testing.assert_frame_equal(
        df.reset_index(drop=True),
        reference.reset_index(drop=True),
        check_dtype=True,
        check_exact=True
    )

    print(
        "PASS: Rebuilt dataset matches original Parquet"
    )


# ============================================================
# STEP 8: SAVE REBUILT PARQUET
# ============================================================

def save_data(df):
    """
    Save the validated dataset to a separate Parquet file.

    The original Parquet is never overwritten.
    """

    print("\nSTEP 7: Saving rebuilt dataset")

    # --------------------------------------------------------
    # Prevent overwriting existing files
    # --------------------------------------------------------

    if OUTPUT_FILE.exists():

        raise FileExistsError(
            f"Output already exists: {OUTPUT_FILE}"
        )

    if OUTPUT_FILE.resolve() == REFERENCE_FILE.resolve():

        raise ValueError(
            "Output cannot overwrite reference dataset"
        )

    # --------------------------------------------------------
    # Create output directory
    # --------------------------------------------------------

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Save dataset
    # --------------------------------------------------------

    df.to_parquet(
        OUTPUT_FILE,
        engine="pyarrow",
        index=False
    )

    # --------------------------------------------------------
    # Verify saved data
    # --------------------------------------------------------

    reloaded = pd.read_parquet(
        OUTPUT_FILE
    )

    pd.testing.assert_frame_equal(
        df.reset_index(drop=True),
        reloaded.reset_index(drop=True),
        check_dtype=True,
        check_exact=True
    )

    print(
        f"PASS: Saved dataset verified"
    )

    print(
        f"Saved file: {OUTPUT_FILE.name}"
    )

    print(
        f"File size: "
        f"{OUTPUT_FILE.stat().st_size / (1024 ** 2):.2f} MB"
    )


# ============================================================
# STEP 9: MAIN PIPELINE
# ============================================================

def main():
    """
    Execute the complete historical CSV consolidation
    workflow.
    """

    print("=" * 55)
    print("AquaInsight — Historical Data Consolidation")
    print("=" * 55)

    # --------------------------------------------------------
    # 1. Discover annual CSV files
    # --------------------------------------------------------

    csv_files = discover_files()

    # --------------------------------------------------------
    # 2. Validate source schemas
    # --------------------------------------------------------

    validate_schemas(csv_files)

    # --------------------------------------------------------
    # 3. Load annual data
    # --------------------------------------------------------

    dataframes = load_annual_data(csv_files)

    # --------------------------------------------------------
    # 4. Consolidate datasets
    # --------------------------------------------------------

    combined = consolidate_data(dataframes)

    # --------------------------------------------------------
    # 5. Validate consolidated dataset
    # --------------------------------------------------------

    validate_combined_data(combined)

    # --------------------------------------------------------
    # 6. Compare against reference Parquet
    # --------------------------------------------------------

    compare_reference(combined)

    # --------------------------------------------------------
    # 7. Save and verify rebuilt Parquet
    # --------------------------------------------------------

    save_data(combined)

    print("\n" + "=" * 55)
    print("CONSOLIDATION COMPLETED SUCCESSFULLY")
    print("=" * 55)


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
