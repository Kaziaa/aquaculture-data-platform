# ============================================================
# AquaInsight — ETL Pipeline Integration Test
#
# Purpose:
# Test the complete ETL pipeline using synthetic data.
#
# This test does not require:
# - Historical BarentsWatch datasets
# - PostgreSQL
# - API credentials
# - Internet access
#
# Suitable for local pytest and GitHub Actions.
# ============================================================

from pathlib import Path

import pandas as pd

from src.clean_fishhealth import run_pipeline


# ============================================================
# TEST DATA GENERATION
# ============================================================

def create_sample_data():
    """
    Create a small synthetic dataset using the original
    Norwegian BarentsWatch column names.

    Four observations represent:
    1. A normal measurement
    2. A lice-threshold exceedance
    3. A locality probably without fish
    4. A reporting conflict and temperature outlier
    """

    base = {
        "Uke": 1,
        "År": 2015,
        "Lokalitetsnummer": 1001,
        "Lokalitetsnavn": "Test Locality A",
        "Voksne hunnlus": 0.2,
        "Lus i bevegelige stadier": 0.1,
        "Fastsittende lus": 0.05,
        "Trolig uten fisk": "Nei",
        "Har telt lakselus": "Ja",
        "Kommunenummer": 4601,
        "Kommune": "Test Kommune",
        "Fylkesnummer": 46,
        "Fylke": "Vestland",
        "Lat": 60.4,
        "Lon": 5.3,
        "Lusegrense uke": 0.5,
        "Over lusegrense uke": "Nei",
        "Sjøtemperatur": 12.0,
        "ProduksjonsområdeId": 3,
        "Produksjonsområde": "Karmøy til Sotra",
        "Lusegrense_original": "0.5",
    }

    # Observation 1: Normal measurement
    row1 = base.copy()

    # Observation 2: Exceeds the lice threshold
    row2 = base.copy()
    row2.update({
        "Uke": 2,
        "Lokalitetsnummer": 1002,
        "Lokalitetsnavn": "Test Locality B",
        "Voksne hunnlus": 0.8,
        "Over lusegrense uke": "Ja",
    })

    # Observation 3: Probably without fish
    row3 = base.copy()
    row3.update({
        "År": 2025,
        "Lokalitetsnummer": 1003,
        "Lokalitetsnavn": "Test Locality C",
        "Voksne hunnlus": None,
        "Lus i bevegelige stadier": None,
        "Fastsittende lus": None,
        "Trolig uten fisk": "Ja",
        "Har telt lakselus": "Nei",
        "Over lusegrense uke": "Ukjent",
        "Sjøtemperatur": None,
    })

    # Observation 4: Reporting conflict and temperature outlier
    row4 = base.copy()
    row4.update({
        "År": 2025,
        "Uke": 2,
        "Lokalitetsnummer": 1004,
        "Lokalitetsnavn": "Test Locality D",
        "Trolig uten fisk": "Ja",
        "Har telt lakselus": "Ja",
        "Sjøtemperatur": 35.0,
    })

    return pd.DataFrame([row1, row2, row3, row4])


# ============================================================
# TEST: COMPLETE ETL PIPELINE
# ============================================================

def test_complete_pipeline(tmp_path):
    """
    Execute the actual ETL pipeline using synthetic data
    and validate its output.
    """

    # --------------------------------------------------------
    # 1. Create input data
    # --------------------------------------------------------

    source_df = create_sample_data()

    source = tmp_path / "sample_source.parquet"

    source_df.to_parquet(
        source,
        engine="pyarrow",
        index=False,
    )

    # --------------------------------------------------------
    # 2. Define temporary output paths
    # --------------------------------------------------------

    output = tmp_path / "pipeline_output.parquet"

    # The pipeline permits a missing notebook reference.
    # This allows testing without a historical reference file.
    reference = tmp_path / "reference_not_available.parquet"

    # --------------------------------------------------------
    # 3. Execute the real ETL pipeline
    # --------------------------------------------------------

    cleaned_df, annual_df = run_pipeline(
        source=source,
        reference=reference,
        output=output,
    )

    # --------------------------------------------------------
    # 4. Verify output file
    # --------------------------------------------------------

    assert output.is_file()

    # --------------------------------------------------------
    # 5. Verify dataset dimensions
    # --------------------------------------------------------

    assert len(cleaned_df) == 4

    assert len(cleaned_df.columns) == 28

    # --------------------------------------------------------
    # 6. Verify annual aggregation
    # --------------------------------------------------------

    assert len(annual_df) == 2

    assert set(annual_df.index) == {2015, 2025}

    assert annual_df.loc[2015, "total_observations"] == 2

    assert annual_df.loc[2025, "total_observations"] == 2

    # --------------------------------------------------------
    # 7. Verify missing measurements
    # --------------------------------------------------------

    assert cleaned_df["adult_female_lice"].isna().sum() == 1

    # --------------------------------------------------------
    # 8. Verify reporting-conflict detection
    # --------------------------------------------------------

    assert cleaned_df["reporting_conflict"].sum() == 1

    # --------------------------------------------------------
    # 9. Verify temperature cleaning
    # --------------------------------------------------------

    assert cleaned_df["temperature_outlier"].sum() == 1

    assert cleaned_df["sea_temperature_clean"].max() <= 30.0

    # --------------------------------------------------------
    # 10. Verify lice exceedance calculations
    # --------------------------------------------------------

    assert cleaned_df["calculated_lice_exceedance"].sum() == 1

    assert cleaned_df["calculated_lice_exceedance"].isna().sum() == 1

    # --------------------------------------------------------
    # 11. Verify annual compliance statistics
    # --------------------------------------------------------

    assert annual_df.loc[2015, "eligible_observations"] == 2

    assert annual_df.loc[2015, "exceedance_observations"] == 1

    assert annual_df.loc[2015, "exceedance_rate"] == 50.0

    assert annual_df.loc[2025, "eligible_observations"] == 1

    assert annual_df.loc[2025, "exceedance_observations"] == 0

    assert annual_df.loc[2025, "exceedance_rate"] == 0.0

    # --------------------------------------------------------
    # 12. Verify saved Parquet file
    # --------------------------------------------------------

    reloaded_df = pd.read_parquet(output)

    pd.testing.assert_frame_equal(
        cleaned_df.reset_index(drop=True),
        reloaded_df.reset_index(drop=True),
        check_dtype=True,
        check_exact=True,
    )
