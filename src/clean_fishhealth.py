"""
AquaInsight — Reproducible BarentsWatch Sea-Lice Cleaning Pipeline

Purpose:
    Transform the consolidated historical BarentsWatch dataset
    into a validated 28-column analytical dataset.

Historical period:
    2015–2025

Expected observations:
    613,601

Features:
    - Source schema validation
    - Column standardization
    - Missing-data assessment
    - Reporting-conflict detection
    - Data-type conversion
    - Temperature outlier screening
    - Extreme sea-lice detection
    - Regulatory threshold validation
    - Calculated compliance indicators
    - Annual compliance statistics
    - Reference dataset comparison
    - Atomic Parquet writing
    - Annual CSV and visualization generation

Execution:
    Run from the project root:

    python -m src.clean_fishhealth

IMPORTANT:
    The source Parquet and notebook reference are never modified.

    The output Parquet is written to a temporary file,
    validated, and then atomically replaced.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from orchestration.atomic_writer import atomic_write_parquet


# ============================================================
# STEP 1: PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "barentswatch_lice_2015_2025.parquet"
)

NOTEBOOK_REFERENCE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "barentswatch_lice_cleaned_2015_2025.parquet"
)

PIPELINE_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "barentswatch_lice_pipeline_2015_2025.parquet"
)

ANNUAL_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "annual_compliance_2015_2025.csv"
)

PLOT_OUTPUT = (
    PROJECT_ROOT
    / "outputs"
    / "annual_lice_exceedance_2015_2025.png"
)

# Exploratory screening threshold.
# This is NOT a regulatory sea-temperature limit.
TEMPERATURE_SCREEN_C = 30.0


# ============================================================
# STEP 2: COLUMN CONFIGURATION
# ============================================================

COLUMN_MAPPING = {

    "Uke": "week",
    "År": "year",

    "Lokalitetsnummer": "locality_id",
    "Lokalitetsnavn": "locality_name",

    "Voksne hunnlus": "adult_female_lice",
    "Lus i bevegelige stadier": "mobile_lice",
    "Fastsittende lus": "attached_lice",

    "Trolig uten fisk": "probably_without_fish",
    "Har telt lakselus": "lice_counted",

    "Kommunenummer": "municipality_id",
    "Kommune": "municipality",

    "Fylkesnummer": "county_id",
    "Fylke": "county",

    "Lat": "latitude",
    "Lon": "longitude",

    "Lusegrense uke": "weekly_lice_limit",
    "Over lusegrense uke": "over_lice_limit",

    "Sjøtemperatur": "sea_temperature",

    "ProduksjonsområdeId": "production_area_id",
    "Produksjonsområde": "production_area",

    "Lusegrense_original": "weekly_lice_limit_original",
}


LICE_COLUMNS = [
    "adult_female_lice",
    "mobile_lice",
    "attached_lice",
]

BOOLEAN_COLUMNS = [
    "probably_without_fish",
    "lice_counted",
    "over_lice_limit",
]

IDENTIFIER_COLUMNS = [
    "municipality_id",
    "county_id",
    "production_area_id",
]

ALLOWED_REPORTING = {

    "probably_without_fish": {"Ja", "Nei"},

    "lice_counted": {"Ja", "Nei"},

    "over_lice_limit": {"Ja", "Nei", "Ukjent"},
}


# ============================================================
# STEP 3: LOAD CONSOLIDATED DATA
# ============================================================

def load_data(path: Path) -> pd.DataFrame:
    """
    Load consolidated BarentsWatch Parquet data.

    The source file is never modified.
    """

    if not path.is_file():

        raise FileNotFoundError(
            f"Source file does not exist: {path}"
        )

    df = pd.read_parquet(path)

    if df.empty:

        raise ValueError(
            "Source dataset is empty"
        )

    print(
        f"Loaded source: "
        f"{len(df):,} rows × {len(df.columns)} columns"
    )

    return df


# ============================================================
# STEP 4: STANDARDIZE COLUMN NAMES
# ============================================================

def standardize_columns(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Validate the source schema and rename columns.

    Column order is preserved.
    """

    missing = (
        set(COLUMN_MAPPING) - set(df.columns)
    )

    unexpected = (
        set(df.columns) - set(COLUMN_MAPPING)
    )

    if (
        missing
        or unexpected
        or len(df.columns) != len(COLUMN_MAPPING)
    ):

        raise ValueError(
            "Unexpected source schema.\n"
            f"Missing: {sorted(missing)}\n"
            f"Additional: {sorted(unexpected)}"
        )

    return df.rename(
        columns=COLUMN_MAPPING
    )


# ============================================================
# STEP 5: MISSING DATA REPORT
# ============================================================

def missing_data_report(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculate missing-value counts and percentages.

    No rows are deleted.
    """

    report = pd.DataFrame({

        "missing_count": df.isna().sum(),

        "missing_percent": (
            df.isna().mean() * 100
        ),
    })

    return report.sort_values(
        "missing_percent",
        ascending=False,
    )


# ============================================================
# STEP 6: REPORTING CROSS-TABULATION
# ============================================================

def reporting_cross_tab(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Examine missing sea-lice measurements in relation
    to source reporting flags.
    """

    return pd.crosstab(

        index=[
            df["probably_without_fish"],
            df["lice_counted"],
        ],

        columns=(
            df["adult_female_lice"].isna()
        ),

        margins=True,
    )


# ============================================================
# STEP 7: FLAG REPORTING CONFLICTS
# ============================================================

def flag_reporting_conflicts(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Identify observations where a locality is flagged
    as probably without fish but lice were counted.

    Preserve the original notebook definition.
    """

    df["reporting_conflict"] = (

        (df["probably_without_fish"] == "Ja")

        &

        (df["lice_counted"] == "Ja")
    )

    return df


# ============================================================
# STEP 8: CONVERT DATA TYPES
# ============================================================

def convert_data_types(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Convert reporting categories to nullable Boolean.

    Convert administrative identifiers to nullable Int64.
    """

    mapping = {

        "Ja": True,
        "Nei": False,
        "Ukjent": pd.NA,
    }

    # Convert reporting columns
    for col in BOOLEAN_COLUMNS:

        actual = set(
            df[col].dropna().unique()
        )

        unexpected = (
            actual - ALLOWED_REPORTING[col]
        )

        if unexpected:

            raise ValueError(
                f"Unexpected reporting values "
                f"in {col}: {unexpected}"
            )

        df[col] = (
            df[col]
            .map(mapping)
            .astype("boolean")
        )

    # Convert administrative identifiers
    for col in IDENTIFIER_COLUMNS:

        nonmissing = df[col].dropna()

        if not pd.api.types.is_numeric_dtype(
            df[col]
        ):

            raise TypeError(
                f"{col} must be numeric before conversion"
            )

        if (nonmissing % 1 != 0).any():

            raise ValueError(
                f"Non-integer administrative IDs in {col}"
            )

        df[col] = df[col].astype("Int64")

    return df


# ============================================================
# STEP 9: NUMERIC DATA QUALITY
# ============================================================

def numeric_quality_report(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Summarize measurements and report negative values.

    No measurements are removed.
    """

    columns = [
        *LICE_COLUMNS,
        "sea_temperature",
    ]

    print(
        "\nNumeric measurement summary:\n",
        df[columns].describe(),
    )

    print(
        "\nNegative values:\n",
        (df[columns] < 0).sum(),
    )

    return df[columns].describe()


# ============================================================
# STEP 10: TEMPERATURE SCREENING
# ============================================================

def clean_temperature(
    df: pd.DataFrame,
    cutoff: float = TEMPERATURE_SCREEN_C,
) -> pd.DataFrame:
    """
    Flag temperatures above a provisional screening cutoff.

    Preserve original sea-temperature values.
    """

    if cutoff <= 0:

        raise ValueError(
            "Temperature screening cutoff must be positive"
        )

    df["temperature_outlier"] = (
        df["sea_temperature"] > cutoff
    )

    df["sea_temperature_clean"] = (
        df["sea_temperature"].mask(
            df["temperature_outlier"]
        )
    )

    return df


# ============================================================
# STEP 11: IDENTIFY EXTREME SEA-LICE OBSERVATIONS
# ============================================================

def flag_extreme_lice(
    df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Flag observations above the 99th percentile.

    Extreme observations are retained.
    """

    thresholds = (
        df[LICE_COLUMNS].quantile(0.99)
    )

    for col in LICE_COLUMNS:

        df[f"{col}_extreme"] = (
            df[col] > thresholds[col]
        )

    return df, thresholds


# ============================================================
# STEP 12: CHECK SOURCE COMPLIANCE
# ============================================================

def check_source_compliance(
    df: pd.DataFrame
) -> dict[str, int]:
    """
    Compare source exceedance indicators against
    two threshold interpretations:

        >
        >=
    """

    eligible = df.loc[

        df["adult_female_lice"].notna()

        & df["weekly_lice_limit"].notna()

        & df["over_lice_limit"].notna()
    ]

    strictly_greater = (

        eligible["adult_female_lice"]

        > eligible["weekly_lice_limit"]
    )

    greater_or_equal = (

        eligible["adult_female_lice"]

        >= eligible["weekly_lice_limit"]
    )

    mismatches_gt = int(

        (
            strictly_greater
            != eligible["over_lice_limit"]
        ).sum()
    )

    mismatches_gte = int(

        (
            greater_or_equal
            != eligible["over_lice_limit"]
        ).sum()
    )

    return {

        "checked": len(eligible),

        "mismatches_gt": mismatches_gt,

        "mismatches_gte": mismatches_gte,
    }


# ============================================================
# STEP 13: CALCULATE SEA-LICE EXCEEDANCE
# ============================================================

def calculate_exceedance(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculate sea-lice threshold exceedance.

    Uses >= to reproduce the historical notebook.

    Rows without a valid lice measurement or threshold
    remain unknown (pd.NA).
    """

    valid = (

        df["adult_female_lice"].notna()

        & df["weekly_lice_limit"].notna()
    )

    df["calculated_lice_exceedance"] = pd.Series(

        pd.NA,

        index=df.index,

        dtype="boolean",
    )

    df.loc[
        valid,
        "calculated_lice_exceedance"
    ] = (

        df.loc[
            valid,
            "adult_female_lice"
        ]

        >=

        df.loc[
            valid,
            "weekly_lice_limit"
        ]
    )

    return df


# ============================================================
# STEP 14: ANNUAL COMPLIANCE REPORT
# ============================================================

def annual_exceedance_report(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculate annual exceedance statistics.
    """

    annual = df.groupby("year").agg(

        total_observations=(
            "locality_id",
            "size",
        ),

        eligible_observations=(
            "calculated_lice_exceedance",
            "count",
        ),

        exceedance_observations=(
            "calculated_lice_exceedance",
            "sum",
        ),
    )

    annual["exceedance_rate"] = (

        annual["exceedance_observations"]

        / annual["eligible_observations"]

        * 100
    )

    return annual


# ============================================================
# STEP 15: SAVE ANNUAL VISUALIZATION
# ============================================================

def save_annual_plot(
    annual: pd.DataFrame,
    path: Path,
) -> None:
    """
    Save the annual exceedance rate visualization.
    """

    import matplotlib

    matplotlib.use("Agg")

    import matplotlib.pyplot as plt

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig, ax = plt.subplots(
        figsize=(10, 5)
    )

    ax.plot(

        annual.index,

        annual["exceedance_rate"],

        marker="o",

        linewidth=2,
    )

    ax.set_title(
        "Sea-Lice Threshold Exceedance Rate (2015–2025)"
    )

    ax.set_xlabel("Year")

    ax.set_ylabel("Exceedance Rate (%)")

    ax.set_xticks(
        annual.index
    )

    ax.grid(
        True,
        alpha=0.3,
    )

    fig.tight_layout()

    fig.savefig(
        path,
        dpi=150,
    )

    plt.close(fig)


# ============================================================
# STEP 16: VALIDATE AGAINST NOTEBOOK REFERENCE
# ============================================================

def validate_against_reference(
    df: pd.DataFrame,
    reference: Path,
) -> None:
    """
    Compare the result against the original notebook dataset.

    Check:
        - Column names and order
        - Data types
        - All values
        - Missing values
        - Row order
    """

    if not reference.is_file():

        print(
            "Reference not found, skipping "
            f"notebook comparison: {reference}"
        )

        return

    expected = pd.read_parquet(
        reference
    )

    pd.testing.assert_frame_equal(

        df.reset_index(drop=True),

        expected.reset_index(drop=True),

        check_dtype=True,

        check_exact=True,
    )

    print(
        "Notebook reference comparison: PASS "
        "(all values and dtypes match)"
    )


# ============================================================
# STEP 17: ATOMIC PARQUET OUTPUT
# ============================================================

def save_and_verify(
    df: pd.DataFrame,
    path: Path,
) -> None:
    """
    Save the cleaned dataset using atomic Parquet writing.

    Workflow:
        1. Write to a temporary file.
        2. Reload and verify the temporary file.
        3. Atomically replace the destination.

    The previous destination is preserved if temporary
    writing or validation fails.
    """

    atomic_write_parquet(
        df,
        path,
    )

    print(
        f"Saved and verified successfully: {path}"
    )


# ============================================================
# STEP 18: MAIN TRANSFORMATION PIPELINE
# ============================================================

def run_pipeline(
    source: Path,
    reference: Path,
    output: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Execute the historical cleaning transformations
    in the original notebook order.
    """

    # --------------------------------------------------------
    # A. Load consolidated data
    # --------------------------------------------------------

    df = load_data(source)

    # --------------------------------------------------------
    # B. Standardize column names
    # --------------------------------------------------------

    df = standardize_columns(df)

    # --------------------------------------------------------
    # C. Missing-data diagnostics
    # --------------------------------------------------------

    print(
        "\nOriginal missing values (top five):\n",
        missing_data_report(df).head(5),
    )

    print(
        "\nMissing lice cross-tab:\n",
        reporting_cross_tab(df),
    )

    # --------------------------------------------------------
    # D. Flag reporting conflicts
    # --------------------------------------------------------

    df = flag_reporting_conflicts(df)

    # --------------------------------------------------------
    # E. Convert data types
    # --------------------------------------------------------

    df = convert_data_types(df)

    # --------------------------------------------------------
    # F. Numeric data-quality diagnostics
    # --------------------------------------------------------

    numeric_quality_report(df)

    # --------------------------------------------------------
    # G. Screen sea-temperature observations
    # --------------------------------------------------------

    df = clean_temperature(df)

    # --------------------------------------------------------
    # H. Flag extreme lice measurements
    # --------------------------------------------------------

    df, thresholds = flag_extreme_lice(df)

    # --------------------------------------------------------
    # I. Compare source compliance indicators
    # --------------------------------------------------------

    compliance_check = check_source_compliance(df)

    # --------------------------------------------------------
    # J. Calculate threshold exceedance
    # --------------------------------------------------------

    df = calculate_exceedance(df)

    # --------------------------------------------------------
    # K. Calculate annual statistics
    # --------------------------------------------------------

    annual = annual_exceedance_report(df)

    # --------------------------------------------------------
    # L. Display diagnostic results
    # --------------------------------------------------------

    print(
        "\n99th-percentile lice thresholds:\n",
        thresholds,
    )

    print(
        "Extreme lice counts:",
        {
            col: int(
                df[f"{col}_extreme"].sum()
            )
            for col in LICE_COLUMNS
        },
    )

    print(
        "Reporting conflicts:",
        int(df["reporting_conflict"].sum()),
    )

    print(
        "Temperature outliers:",
        int(df["temperature_outlier"].sum()),
    )

    print(
        "Original temperature maximum:",
        df["sea_temperature"].max(),
    )

    print(
        "Clean temperature maximum:",
        df["sea_temperature_clean"].max(),
    )

    print(
        "Compliance comparison:",
        compliance_check,
    )

    print(
        "Calculated exceedances:",
        int(
            df["calculated_lice_exceedance"].sum()
        ),
    )

    print(
        "Missing calculated indicators:",
        int(
            df["calculated_lice_exceedance"].isna().sum()
        ),
    )

    print(
        "\nAnnual exceedance report:\n",
        annual.round(2),
    )

    print(
        f"\nFinal dimensions: "
        f"{len(df):,} rows × {len(df.columns)} columns"
    )

    # --------------------------------------------------------
    # M. Validate expected output structure
    # --------------------------------------------------------

    if len(df.columns) != 28:

        raise AssertionError(
            f"Expected 28 columns; "
            f"got {len(df.columns)}"
        )

    # --------------------------------------------------------
    # N. Compare against the notebook reference
    # --------------------------------------------------------

    # Validate BEFORE replacing the output.

    validate_against_reference(
        df,
        reference,
    )

    # --------------------------------------------------------
    # O. Save using atomic Parquet writing
    # --------------------------------------------------------

    save_and_verify(
        df,
        output,
    )

    return df, annual


# ============================================================
# STEP 19: COMMAND-LINE INTERFACE
# ============================================================

def main() -> None:
    """
    Execute the complete cleaning pipeline.
    """

    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=SOURCE_FILE,
    )

    parser.add_argument(
        "--reference",
        type=Path,
        default=NOTEBOOK_REFERENCE,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=PIPELINE_OUTPUT,
    )

    parser.add_argument(
        "--annual-output",
        type=Path,
        default=ANNUAL_OUTPUT,
    )

    parser.add_argument(
        "--plot-output",
        type=Path,
        default=PLOT_OUTPUT,
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # Protect source and reference files
    # --------------------------------------------------------

    paths = [
        p.resolve()
        for p in (
            args.input,
            args.reference,
            args.output,
        )
    ]

    if paths[2] in paths[:2]:

        parser.error(
            "--output must differ from "
            "--input and --reference"
        )

    # --------------------------------------------------------
    # Execute transformation pipeline
    # --------------------------------------------------------

    print(
        "AquaInsight — Reusable Fish Health ETL Pipeline"
    )

    _, annual = run_pipeline(

        args.input,

        args.reference,

        args.output,
    )

    # --------------------------------------------------------
    # Save annual statistics
    # --------------------------------------------------------

    args.annual_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    annual.to_csv(
        args.annual_output,
        index=True,
    )

    print(
        "Saved annual summary:",
        args.annual_output,
    )

    # --------------------------------------------------------
    # Save annual visualization
    # --------------------------------------------------------

    save_annual_plot(
        annual,
        args.plot_output,
    )

    print(
        "Saved chart:",
        args.plot_output,
    )

    print(
        "Pipeline finished successfully"
    )


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
