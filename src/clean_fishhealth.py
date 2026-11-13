"""AquaInsight — reproducible BarentsWatch sea-lice cleaning pipeline.

Recreates the 28-column output of notebooks/02_data_cleaning.ipynb.

Run from the project root (or any other directory):
    python src/clean_fishhealth.py

Requires: pandas, pyarrow, matplotlib (for the saved plot).

The source Parquet is never modified. This script compares the result with
an existing notebook-produced reference file before writing its own output.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_FILE = PROJECT_ROOT / "data/processed/barentswatch_lice_2015_2025.parquet"
NOTEBOOK_REFERENCE = PROJECT_ROOT / "data/processed/barentswatch_lice_cleaned_2015_2025.parquet"
PIPELINE_OUTPUT = PROJECT_ROOT / "data/processed/barentswatch_lice_pipeline_2015_2025.parquet"
ANNUAL_OUTPUT = PROJECT_ROOT / "data/processed/annual_compliance_2015_2025.csv"
PLOT_OUTPUT = PROJECT_ROOT / "outputs/annual_lice_exceedance_2015_2025.png"
TEMPERATURE_SCREEN_C = 30.0  # Exploratory screening rule; not a regulatory cutoff.

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

LICE_COLUMNS = ["adult_female_lice", "mobile_lice", "attached_lice"]
BOOLEAN_COLUMNS = ["probably_without_fish", "lice_counted", "over_lice_limit"]
IDENTIFIER_COLUMNS = ["municipality_id", "county_id", "production_area_id"]
ALLOWED_REPORTING = {
    "probably_without_fish": {"Ja", "Nei"},
    "lice_counted": {"Ja", "Nei"},
    "over_lice_limit": {"Ja", "Nei", "Ukjent"},
}


def load_data(path: Path) -> pd.DataFrame:
    """Load the original consolidated Parquet (never the cleaned output)."""
    if not path.is_file():
        raise FileNotFoundError(f"Source file does not exist: {path}")
    df = pd.read_parquet(path)
    if df.empty:
        raise ValueError("Source dataset is empty")
    print(f"Loaded source: {len(df):,} rows × {len(df.columns)} columns")
    return df


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Validate the source schema, then rename columns in their original order."""
    missing = set(COLUMN_MAPPING) - set(df.columns)
    unexpected = set(df.columns) - set(COLUMN_MAPPING)
    if missing or unexpected or len(df.columns) != len(COLUMN_MAPPING):
        raise ValueError(
            f"Unexpected source schema; missing={sorted(missing)}, "
            f"additional={sorted(unexpected)}"
        )
    return df.rename(columns=COLUMN_MAPPING)


def missing_data_report(df: pd.DataFrame) -> pd.DataFrame:
    """Describe missingness without changing or dropping rows."""
    return pd.DataFrame({
        "missing_count": df.isna().sum(),
        "missing_percent": df.isna().mean() * 100,
    }).sort_values("missing_percent", ascending=False)


def reporting_cross_tab(df: pd.DataFrame) -> pd.DataFrame:
    """Investigate missing lice counts versus the original Norwegian flags."""
    return pd.crosstab(
        index=[df["probably_without_fish"], df["lice_counted"]],
        columns=df["adult_female_lice"].isna(),
        margins=True,
    )


def flag_reporting_conflicts(df: pd.DataFrame) -> pd.DataFrame:
    """Replicate the notebook's flag BEFORE categorical conversion."""
    df["reporting_conflict"] = (
        (df["probably_without_fish"] == "Ja")
        & (df["lice_counted"] == "Ja")
    )
    return df


def convert_data_types(df: pd.DataFrame) -> pd.DataFrame:
    """Convert known categorical values and numeric administrative IDs."""
    mapping = {"Ja": True, "Nei": False, "Ukjent": pd.NA}
    for col in BOOLEAN_COLUMNS:
        actual = set(df[col].dropna().unique())
        unexpected = actual - ALLOWED_REPORTING[col]
        if unexpected:
            raise ValueError(f"Unexpected reporting values in {col}: {unexpected}")
        df[col] = df[col].map(mapping).astype("boolean")

    for col in IDENTIFIER_COLUMNS:
        nonmissing = df[col].dropna()
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise TypeError(f"{col} must be numeric before conversion")
        if (nonmissing % 1 != 0).any():
            raise ValueError(f"Non-integer administrative IDs in {col}")
        df[col] = df[col].astype("Int64")
    return df


def numeric_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    """Describe measurements; keep negative-value counts separately."""
    columns = [*LICE_COLUMNS, "sea_temperature"]
    print("\nNumeric measurement summary:\n", df[columns].describe())
    print("\nNegative values:\n", (df[columns] < 0).sum())
    return df[columns].describe()


def clean_temperature(df: pd.DataFrame, cutoff: float = TEMPERATURE_SCREEN_C) -> pd.DataFrame:
    """Keep the source values; mask temperatures above a provisional cutoff."""
    if cutoff <= 0:
        raise ValueError("Temperature screening cutoff must be positive")
    df["temperature_outlier"] = df["sea_temperature"] > cutoff
    df["sea_temperature_clean"] = df["sea_temperature"].mask(
        df["temperature_outlier"]
    )
    return df


def flag_extreme_lice(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Flag (do not delete) measurements above each column's 99th percentile."""
    thresholds = df[LICE_COLUMNS].quantile(0.99)
    for col in LICE_COLUMNS:
        df[f"{col}_extreme"] = df[col] > thresholds[col]
    return df, thresholds


def check_source_compliance(df: pd.DataFrame) -> dict[str, int]:
    """Reproduce the notebook's > versus >= comparison for eligible rows."""
    eligible = df.loc[
        df["adult_female_lice"].notna()
        & df["weekly_lice_limit"].notna()
        & df["over_lice_limit"].notna()
    ]
    strictly_greater = eligible["adult_female_lice"] > eligible["weekly_lice_limit"]
    greater_or_equal = eligible["adult_female_lice"] >= eligible["weekly_lice_limit"]
    mismatches_gt = int((strictly_greater != eligible["over_lice_limit"]).sum())
    mismatches_gte = int((greater_or_equal != eligible["over_lice_limit"]).sum())
    return {
        "checked": len(eligible),
        "mismatches_gt": mismatches_gt,
        "mismatches_gte": mismatches_gte,
    }


def calculate_exceedance(df: pd.DataFrame) -> pd.DataFrame:
    """Reproduce source indicator using >=, leaving ineligible rows unknown."""
    valid = df["adult_female_lice"].notna() & df["weekly_lice_limit"].notna()
    df["calculated_lice_exceedance"] = pd.Series(
        pd.NA, index=df.index, dtype="boolean"
    )
    df.loc[valid, "calculated_lice_exceedance"] = (
        df.loc[valid, "adult_female_lice"]
        >= df.loc[valid, "weekly_lice_limit"]
    )
    return df


def annual_exceedance_report(df: pd.DataFrame) -> pd.DataFrame:
    """Count locality-week rows, eligible rows and >= threshold rows by year."""
    annual = df.groupby("year").agg(
        total_observations=("locality_id", "size"),
        eligible_observations=("calculated_lice_exceedance", "count"),
        exceedance_observations=("calculated_lice_exceedance", "sum"),
    )
    annual["exceedance_rate"] = (
        annual["exceedance_observations"] / annual["eligible_observations"] * 100
    )
    return annual


def save_annual_plot(annual: pd.DataFrame, path: Path) -> None:
    """Save the annual exceedance line plot without opening a GUI."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(annual.index, annual["exceedance_rate"], marker="o", linewidth=2)
    ax.set_title("Sea-Lice Threshold Exceedance Rate (2015–2025)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Exceedance Rate (%)")
    ax.set_xticks(annual.index)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def validate_against_reference(df: pd.DataFrame, reference: Path) -> None:
    """Check full column order, types and values against notebook-created Parquet."""
    if not reference.is_file():
        print(f"Reference not found, skipping notebook comparison: {reference}")
        return
    expected = pd.read_parquet(reference)
    pd.testing.assert_frame_equal(
        df.reset_index(drop=True),
        expected.reset_index(drop=True),
        check_dtype=True,
        check_exact=True,
    )
    print("Notebook reference comparison: PASS (all values and dtypes match)")


def save_and_verify(df: pd.DataFrame, path: Path) -> None:
    """Write a NEW Parquet file and prove that it round-trips losslessly."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, engine="pyarrow", index=False)
    reloaded = pd.read_parquet(path)
    pd.testing.assert_frame_equal(
        df.reset_index(drop=True), reloaded, check_dtype=True, check_exact=True
    )
    print(f"Saved and reloaded successfully: {path}")


def run_pipeline(source: Path, reference: Path, output: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the notebook-equivalent transforms in precisely the same order."""
    df = load_data(source)
    df = standardize_columns(df)

    # Diagnostics correspond to notebook's early exploratory cells.
    print("\nOriginal missing values (top five):\n", missing_data_report(df).head(5))
    print("\nMissing lice cross-tab:\n", reporting_cross_tab(df))

    # Preserve the notebook's column order (the conflict flag is column 22).
    df = flag_reporting_conflicts(df)
    df = convert_data_types(df)
    numeric_quality_report(df)
    df = clean_temperature(df)
    df, thresholds = flag_extreme_lice(df)
    compliance_check = check_source_compliance(df)
    df = calculate_exceedance(df)
    annual = annual_exceedance_report(df)

    print("\n99th-percentile lice thresholds:\n", thresholds)
    print("Extreme lice counts:", {
        col: int(df[f"{col}_extreme"].sum()) for col in LICE_COLUMNS
    })
    print("Reporting conflicts:", int(df["reporting_conflict"].sum()))
    print("Temperature outliers:", int(df["temperature_outlier"].sum()))
    print("Original temperature maximum:", df["sea_temperature"].max())
    print("Clean temperature maximum:", df["sea_temperature_clean"].max())
    print("Compliance comparison:", compliance_check)
    print("Calculated exceedances:", int(df["calculated_lice_exceedance"].sum()))
    print("Missing calculated indicators:", int(df["calculated_lice_exceedance"].isna().sum()))
    print("\nAnnual exceedance report:\n", annual.round(2))
    print(f"\nFinal dimensions: {len(df):,} rows × {len(df.columns)} columns")

    if len(df.columns) != 28:
        raise AssertionError(f"Expected 28 columns; got {len(df.columns)}")
    # Compare before writing, so an incorrect transform cannot overwrite a valid output.
    validate_against_reference(df, reference)
    save_and_verify(df, output)
    return df, annual


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=SOURCE_FILE)
    parser.add_argument("--reference", type=Path, default=NOTEBOOK_REFERENCE)
    parser.add_argument("--output", type=Path, default=PIPELINE_OUTPUT)
    parser.add_argument("--annual-output", type=Path, default=ANNUAL_OUTPUT)
    parser.add_argument("--plot-output", type=Path, default=PLOT_OUTPUT)
    args = parser.parse_args()

    # Never overwrite either the source data or the notebook reference.
    paths = [p.resolve() for p in (args.input, args.reference, args.output)]
    if paths[2] in paths[:2]:
        parser.error("--output must differ from --input and --reference")

    print("AquaInsight — Reusable Fish Health ETL Pipeline")
    _, annual = run_pipeline(args.input, args.reference, args.output)
    args.annual_output.parent.mkdir(parents=True, exist_ok=True)
    annual.to_csv(args.annual_output, index=True)
    print("Saved annual summary:", args.annual_output)
    save_annual_plot(annual, args.plot_output)
    print("Saved chart:", args.plot_output)
    print("Pipeline finished successfully")


if __name__ == "__main__":
    main()