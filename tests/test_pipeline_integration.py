# ============================================================
# AquaInsight — ETL Pipeline Integration Test
#
# Purpose:
# Verify the complete ETL pipeline using real historical data.
# ============================================================

from pathlib import Path

import pandas as pd
import pytest

from src.clean_fishhealth import run_pipeline


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    PROJECT_ROOT
    / "data/processed/barentswatch_lice_2015_2025.parquet"
)

REFERENCE = (
    PROJECT_ROOT
    / "data/processed/barentswatch_lice_cleaned_2015_2025.parquet"
)


# ============================================================
# TEST 11: COMPLETE ETL PIPELINE
# ============================================================

def test_complete_pipeline(tmp_path):

    # Check that the actual source dataset exists
    assert SOURCE.is_file(), f"Missing source: {SOURCE}"

    # Check that the notebook reference exists
    assert REFERENCE.is_file(), f"Missing reference: {REFERENCE}"

    # Create a temporary output location
    output = tmp_path / "pipeline_test_output.parquet"

    # Execute the complete ETL pipeline
    cleaned_df, annual_df = run_pipeline(
        source=SOURCE,
        reference=REFERENCE,
        output=output
    )

    # Verify output file was created
    assert output.is_file()

    # Verify number of observations
    assert len(cleaned_df) == 613601

    # Verify expected number of columns
    assert len(cleaned_df.columns) == 28

    # Verify annual report contains 11 years
    assert len(annual_df) == 11

    # Verify the years represented
    assert set(annual_df.index) == set(range(2015, 2026))

    # Reload the saved output
    reloaded_df = pd.read_parquet(output)

    # Verify saved output matches returned DataFrame
    pd.testing.assert_frame_equal(
        cleaned_df.reset_index(drop=True),
        reloaded_df.reset_index(drop=True),
        check_dtype=True,
        check_exact=True
    )
