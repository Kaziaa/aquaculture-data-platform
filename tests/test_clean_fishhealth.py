# ============================================================
# AquaInsight — Automated ETL Pipeline Tests
#
# Test 1: Temperature cleaning
# Test 2: Missing-data reporting
# Test 3: Compliance calculation
# Test 4: Data type conversion
# ============================================================

import pandas as pd
import pytest

from src.clean_fishhealth import (
    clean_temperature,
    missing_data_report,
    calculate_exceedance,
    convert_data_types
)


# ============================================================
# TEST 1: TEMPERATURE CLEANING
# ============================================================

def test_temperature_cleaning():

    test_data = pd.DataFrame({
        "sea_temperature": [
            8.5, 15.2, 35.0, 196.18, None
        ]
    })

    original_data = test_data.copy(deep=True)

    result = clean_temperature(test_data)

    # Normal temperatures remain unchanged
    assert result["sea_temperature_clean"].iloc[0] == 8.5
    assert result["sea_temperature_clean"].iloc[1] == 15.2

    # Extreme temperatures are flagged
    assert result["temperature_outlier"].iloc[2]
    assert result["temperature_outlier"].iloc[3]

    # Extreme temperatures become missing
    assert pd.isna(result["sea_temperature_clean"].iloc[2])
    assert pd.isna(result["sea_temperature_clean"].iloc[3])

    # Original temperature measurements are preserved
    pd.testing.assert_series_equal(
        result["sea_temperature"],
        original_data["sea_temperature"]
    )

    # Existing missing values remain missing
    assert pd.isna(result["sea_temperature_clean"].iloc[4])

    # No observations are deleted
    assert len(result) == 5


# ============================================================
# TEST 2: MISSING-DATA REPORTING
# ============================================================

def test_missing_data_report():

    test_data = pd.DataFrame({
        "adult_female_lice": [
            0.1, 0.2, None, 0.4, None
        ],
        "sea_temperature": [
            8.0, None, 10.0, 12.0, 14.0
        ]
    })

    original_data = test_data.copy(deep=True)

    result = missing_data_report(test_data)

    assert result.loc[
        "adult_female_lice", "missing_count"
    ] == 2

    assert result.loc[
        "sea_temperature", "missing_count"
    ] == 1

    assert result.loc[
        "adult_female_lice", "missing_percent"
    ] == 40.0

    assert result.loc[
        "sea_temperature", "missing_percent"
    ] == 20.0

    pd.testing.assert_frame_equal(
        test_data,
        original_data
    )


# ============================================================
# TEST 3: COMPLIANCE CALCULATION
# ============================================================

def test_compliance_calculation():

    test_data = pd.DataFrame({
        "adult_female_lice": [
            0.30, 0.50, 0.80, None
        ],
        "weekly_lice_limit": [
            0.50, 0.50, 0.50, 0.50
        ]
    })

    result = calculate_exceedance(test_data)

    # Below threshold
    assert result["calculated_lice_exceedance"].iloc[0] == False

    # Equal to threshold
    assert result["calculated_lice_exceedance"].iloc[1] == True

    # Above threshold
    assert result["calculated_lice_exceedance"].iloc[2] == True

    # Missing measurement
    assert pd.isna(
        result["calculated_lice_exceedance"].iloc[3]
    )

    assert str(
        result["calculated_lice_exceedance"].dtype
    ) == "boolean"

    assert len(result) == 4


# ============================================================
# TEST 4: DATA TYPE CONVERSION
# ============================================================

def test_data_type_conversion():

    test_data = pd.DataFrame({
        "probably_without_fish": [
            "Nei", "Ja", "Nei"
        ],
        "lice_counted": [
            "Ja", "Nei", "Ja"
        ],
        "over_lice_limit": [
            "Ja", "Nei", "Ukjent"
        ],
        "municipality_id": [
            1219.0, 1243.0, None
        ],
        "county_id": [
            12.0, 12.0, None
        ],
        "production_area_id": [
            3.0, 3.0, None
        ]
    })

    result = convert_data_types(test_data)

    # Verify Boolean conversion
    assert result["over_lice_limit"].iloc[0] == True
    assert result["over_lice_limit"].iloc[1] == False

    # Unknown compliance must remain missing
    assert pd.isna(result["over_lice_limit"].iloc[2])

    # Verify nullable Boolean data type
    assert str(result["over_lice_limit"].dtype) == "boolean"

    # Verify identifier conversion
    assert str(result["municipality_id"].dtype) == "Int64"
    assert str(result["county_id"].dtype) == "Int64"
    assert str(result["production_area_id"].dtype) == "Int64"

    # Verify values
    assert result["municipality_id"].iloc[0] == 1219

    # Missing identifier remains missing
    assert pd.isna(result["municipality_id"].iloc[2])

    # No rows are deleted
    assert len(result) == 3


# ============================================================
# TEST 5: REJECT INVALID REPORTING VALUES
# ============================================================

def test_invalid_reporting_value():

    test_data = pd.DataFrame({
        "probably_without_fish": ["Nei"],
        "lice_counted": ["Ja"],
        "over_lice_limit": ["Maybe"],
        "municipality_id": [1219.0],
        "county_id": [12.0],
        "production_area_id": [3.0]
    })

    with pytest.raises(ValueError):
        convert_data_types(test_data)



# ============================================================
# TEST 6: COLUMN STANDARDIZATION
# ============================================================

def test_column_standardization():

    from src.clean_fishhealth import standardize_columns

    # Create a small dataset containing the complete source schema
    column_names = {
        "Uke": 1,
        "År": 2025,
        "Lokalitetsnummer": 12345,
        "Lokalitetsnavn": "Test Locality",
        "Voksne hunnlus": 0.2,
        "Lus i bevegelige stadier": 0.4,
        "Fastsittende lus": 0.1,
        "Trolig uten fisk": "Nei",
        "Har telt lakselus": "Ja",
        "Kommunenummer": 4601,
        "Kommune": "Bergen",
        "Fylkesnummer": 46,
        "Fylke": "Vestland",
        "Lat": 60.39,
        "Lon": 5.32,
        "Lusegrense uke": 0.5,
        "Over lusegrense uke": "Nei",
        "Sjøtemperatur": 10.5,
        "ProduksjonsområdeId": 3,
        "Produksjonsområde": "Test Area",
        "Lusegrense_original": "0.5"
    }

    test_data = pd.DataFrame([column_names])

    # Execute the actual ETL function
    result = standardize_columns(test_data)

    # Verify important column names
    assert "year" in result.columns
    assert "week" in result.columns
    assert "locality_id" in result.columns
    assert "adult_female_lice" in result.columns

    # Original Norwegian names should be replaced
    assert "År" not in result.columns
    assert "Voksne hunnlus" not in result.columns

    # All 21 columns should remain
    assert len(result.columns) == 21

    # Data values must remain unchanged
    assert result["year"].iloc[0] == 2025
    assert result["adult_female_lice"].iloc[0] == 0.2


# ============================================================
# TEST 7: REJECT MISSING REQUIRED COLUMNS
# ============================================================

def test_missing_required_columns():

    from src.clean_fishhealth import standardize_columns

    # Deliberately incomplete dataset
    test_data = pd.DataFrame({
        "År": [2025],
        "Uke": [1]
    })

    # The function should reject the incomplete schema
    with pytest.raises(ValueError):
        standardize_columns(test_data)



# ============================================================
# TEST 8: REPORTING-CONFLICT DETECTION
# ============================================================

def test_reporting_conflict_detection():

    from src.clean_fishhealth import flag_reporting_conflicts

    # Create test data using original Norwegian categories
    test_data = pd.DataFrame({
        "probably_without_fish": [
            "Ja", "Ja", "Nei", "Nei"
        ],
        "lice_counted": [
            "Ja", "Nei", "Ja", "Nei"
        ]
    })

    # Execute the actual ETL function
    result = flag_reporting_conflicts(test_data)

    # Expected reporting-conflict values
    expected = [True, False, False, False]

    # Verify correct flags
    assert result["reporting_conflict"].tolist() == expected

    # Verify exactly one reporting conflict
    assert result["reporting_conflict"].sum() == 1

    # Verify no observations were deleted
    assert len(result) == 4

    # ============================================================
# TEST 9: EXTREME SEA-LICE DETECTION
# ============================================================

def test_extreme_lice_detection():

    from src.clean_fishhealth import (
        flag_extreme_lice,
        LICE_COLUMNS
    )

    # Create 100 controlled observations
    test_data = pd.DataFrame({
        col: [0.2] * 99 + [10.0]
        for col in LICE_COLUMNS
    })

    # Preserve original measurements
    original_data = test_data.copy(deep=True)

    # Run the actual ETL function
    result, thresholds = flag_extreme_lice(test_data)

    # Test each sea-lice measurement column
    for col in LICE_COLUMNS:

        flag_column = f"{col}_extreme"

        # Verify the flag column exists
        assert flag_column in result.columns

        # Only the final observation should be flagged
        assert result[flag_column].iloc[-1]

        # First observation should not be flagged
        assert not result[flag_column].iloc[0]

        # Exactly one observation should be flagged
        assert result[flag_column].sum() == 1

        # Verify the calculated 99th percentile
        expected_threshold = original_data[col].quantile(0.99)

        assert thresholds[col] == pytest.approx(
            expected_threshold
        )

        # Verify original measurement values are preserved
        pd.testing.assert_series_equal(
            result[col],
            original_data[col]
        )

    # Verify no observations were deleted
    assert len(result) == 100



# ============================================================
# TEST 10: SOURCE COMPLIANCE VALIDATION
# ============================================================

def test_source_compliance_validation():

    from src.clean_fishhealth import check_source_compliance

    # Create controlled test observations
    test_data = pd.DataFrame({
        "adult_female_lice": [
            0.30,
            0.50,
            0.80,
            None
        ],

        "weekly_lice_limit": [
            0.50,
            0.50,
            0.50,
            0.50
        ],

        "over_lice_limit": pd.Series(
            [False, True, True, pd.NA],
            dtype="boolean"
        )
    })

    # Execute the actual ETL function
    result = check_source_compliance(test_data)

    # Three observations are eligible
    assert result["checked"] == 3

    # Strictly greater than produces one mismatch
    assert result["mismatches_gt"] == 1

    # Greater than or equal produces zero mismatches
    assert result["mismatches_gte"] == 0

    # Verify the function returns a dictionary
    assert isinstance(result, dict)
