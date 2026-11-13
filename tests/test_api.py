# ============================================================
# AquaInsight — FastAPI Automated Tests
# Day 9 — Task 9.20
#
# Tests:
#   1. API health check
#   2. Unavailable year validation
#   3. Annual summary endpoint
#   4. Production-area endpoint
#   5. Database failure handling
#   6. Engine shutdown cleanup
#   7. Invalid percentage response
#   8. Exceedances greater than eligible observations
#   9. Percentage consistency
#  10. Valid statistical records
# ============================================================

from unittest.mock import MagicMock

import pytest

from fastapi.testclient import TestClient
from fastapi.exceptions import ResponseValidationError

from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from api.main import app
from api.schemas import ProductionAreaRecord


# ============================================================
# CREATE TEST CLIENT
# ============================================================

client = TestClient(app)


# ============================================================
# TEST 1: API HEALTH CHECK
# ============================================================

def test_health_check():

    response = client.get("/api/v1/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "AquaInsight"


# ============================================================
# TEST 2: UNAVAILABLE YEAR VALIDATION
# ============================================================

def test_invalid_year(monkeypatch):

    # Simulate the years available in PostgreSQL
    mock_years = list(range(2015, 2026))

    # Replace the real database function
    monkeypatch.setattr(
        "api.main.get_available_years",
        lambda: mock_years
    )

    # Request a year not available in the database
    response = client.get("/api/v1/production-areas/2035")

    # An unavailable integer year should return HTTP 404
    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == (
        "No aquaculture data available for year 2035"
    )


# ============================================================
# TEST 3: ANNUAL SUMMARY WITH MOCK DATABASE
# ============================================================

def test_annual_summary(monkeypatch):

    # Simulated PostgreSQL result
    mock_data = [
        {
            "year": 2025,
            "total_observations": 55646,
            "unique_localities": 1081,
            "valid_lice_measurements": 30299,
            "missing_lice_measurements": 25347,
            "average_adult_female_lice": 0.177,
            "lice_exceedances": 1066,
            "eligible_compliance_observations": 30298,
            "exceedance_percentage": 3.52
        }
    ]

    # Create a simulated SQLAlchemy Engine
    mock_engine = MagicMock()

    # Simulate the database connection
    mock_connection = (
        mock_engine.connect.return_value.__enter__.return_value
    )

    # Simulate the database query result
    mock_connection.execute.return_value.mappings.return_value.all.return_value = (
        mock_data
    )

    # Replace the real database Engine
    monkeypatch.setattr(
        "api.main.get_engine",
        lambda: mock_engine
    )

    # Send an HTTP request
    response = client.get("/api/v1/annual-summary")

    # Verify HTTP status
    assert response.status_code == 200

    # Read JSON response
    data = response.json()

    # Verify response structure
    assert data["status"] == "success"
    assert data["total_years"] == 1

    # Verify annual statistics
    assert data["data"][0]["year"] == 2025
    assert data["data"][0]["total_observations"] == 55646
    assert data["data"][0]["lice_exceedances"] == 1066
    assert data["data"][0]["exceedance_percentage"] == 3.52

    # Verify SQL query execution
    mock_connection.execute.assert_called_once()

    # The shared Engine must not be disposed of after a request
    mock_engine.dispose.assert_not_called()


# ============================================================
# TEST 4: PRODUCTION-AREA API WITH MOCK DATABASE
# ============================================================

def test_production_areas(monkeypatch):

    # Simulated PostgreSQL records
    mock_data = [
        {
            "production_area_id": 6,
            "production_area": "Nordmøre og Sør-Trøndelag",
            "unique_localities": 143,
            "eligible_observations": 4628,
            "exceedance_observations": 291,
            "exceedance_percentage": 6.29
        },
        {
            "production_area_id": 3,
            "production_area": "Karmøy til Sotra",
            "unique_localities": 154,
            "eligible_observations": 4276,
            "exceedance_observations": 235,
            "exceedance_percentage": 5.50
        }
    ]

    # Create a simulated SQLAlchemy Engine
    mock_engine = MagicMock()

    # Simulate the database connection
    mock_connection = (
        mock_engine.connect.return_value.__enter__.return_value
    )

    # Configure the simulated SQL query result
    mock_connection.execute.return_value.mappings.return_value.all.return_value = (
        mock_data
    )

    # Replace the real database Engine
    monkeypatch.setattr(
        "api.main.get_engine",
        lambda: mock_engine
    )

    # IMPORTANT:
    # The production-area endpoint now checks available years
    # before executing the statistics query.
    #
    # Mock this function so the test never needs PostgreSQL.
    monkeypatch.setattr(
        "api.main.get_available_years",
        lambda: [2023, 2024, 2025]
    )

    # Send an HTTP request
    response = client.get("/api/v1/production-areas/2025")

    # Verify HTTP status
    assert response.status_code == 200

    # Read JSON response
    data = response.json()

    # Verify response structure
    assert data["status"] == "success"
    assert data["year"] == 2025
    assert data["total_production_areas"] == 2

    # Verify production-area statistics
    assert data["data"][0]["production_area_id"] == 6
    assert data["data"][0]["exceedance_percentage"] == 6.29

    assert data["data"][1]["production_area_id"] == 3
    assert data["data"][1]["exceedance_percentage"] == 5.50

    # Verify the SQL query was executed once
    mock_connection.execute.assert_called_once()

    # Verify that the correct year was passed to SQLAlchemy
    args, kwargs = mock_connection.execute.call_args

    assert args[1] == {"year": 2025}

    # The shared Engine must not be disposed of after a request
    mock_engine.dispose.assert_not_called()


# ============================================================
# TEST 5: DATABASE QUERY FAILURE
# ============================================================

def test_annual_summary_database_failure(monkeypatch):

    # Create a simulated SQLAlchemy Engine
    mock_engine = MagicMock()

    # Simulate the database connection
    mock_connection = (
        mock_engine.connect.return_value.__enter__.return_value
    )

    # Simulate a PostgreSQL query failure
    mock_connection.execute.side_effect = OperationalError(
        statement="SELECT * FROM aquainsight.v_annual_lice_summary",
        params={},
        orig=Exception("Simulated database connection failure")
    )

    # Replace the real database Engine
    monkeypatch.setattr(
        "api.main.get_engine",
        lambda: mock_engine
    )

    # Send an HTTP request
    response = client.get("/api/v1/annual-summary")

    # Verify HTTP 503
    assert response.status_code == 503

    data = response.json()

    # Verify the error message
    assert data["detail"] == "Annual summary data unavailable"

    # Verify the SQL query was attempted
    mock_connection.execute.assert_called_once()

    # The shared Engine must not be disposed of after a failed request
    mock_engine.dispose.assert_not_called()


# ============================================================
# TEST 6: APPLICATION SHUTDOWN CLEANS UP SHARED ENGINE
# ============================================================

def test_engine_disposal_on_shutdown(monkeypatch):

    from src.database import get_engine

    # Clear any previously cached Engine
    get_engine.cache_clear()

    # Create a simulated SQLAlchemy Engine
    mock_engine = MagicMock()

    # Replace the real SQLAlchemy Engine factory
    monkeypatch.setattr(
        "src.database.create_engine",
        lambda *args, **kwargs: mock_engine
    )

    # Start and stop FastAPI using a context manager
    with TestClient(app) as test_client:

        # Make a request that does not require PostgreSQL
        response = test_client.get("/api/v1/health")

        assert response.status_code == 200

        # Create the cached Engine while FastAPI is running
        engine = get_engine()

        assert engine is mock_engine

        # Engine must remain available during application operation
        mock_engine.dispose.assert_not_called()

    # Exiting TestClient triggers application shutdown

    # Verify the Engine was disposed of once
    mock_engine.dispose.assert_called_once()

    # Verify the Engine cache was cleared
    assert get_engine.cache_info().currsize == 0


# ============================================================
# TEST 7: PYDANTIC RESPONSE VALIDATION
# ============================================================

def test_invalid_production_area_response(monkeypatch):

    # Simulate a database record containing invalid data
    mock_data = [
        {
            "production_area_id": 6,
            "production_area": "Nordmøre og Sør-Trøndelag",
            "unique_localities": 143,
            "eligible_observations": 4628,
            "exceedance_observations": 291,
            "exceedance_percentage": 150.0
        }
    ]

    # Create a simulated SQLAlchemy Engine
    mock_engine = MagicMock()

    # Simulate the database connection
    mock_connection = (
        mock_engine.connect.return_value.__enter__.return_value
    )

    # Configure simulated SQL results
    mock_connection.execute.return_value.mappings.return_value.all.return_value = (
        mock_data
    )

    # Replace the real database Engine
    monkeypatch.setattr(
        "api.main.get_engine",
        lambda: mock_engine
    )

    # Mock available reporting years
    monkeypatch.setattr(
        "api.main.get_available_years",
        lambda: [2025]
    )

    # Expect FastAPI to reject the invalid response
    with pytest.raises(ResponseValidationError) as error_info:

        client.get("/api/v1/production-areas/2025")

    # Retrieve validation errors
    errors = error_info.value.errors()

    # Verify that the percentage field caused validation failure
    assert any(
        "exceedance_percentage" in str(error["loc"])
        for error in errors
    )

    # Engine must remain available
    mock_engine.dispose.assert_not_called()


# ============================================================
# TEST 8: CROSS-FIELD VALIDATION
# ============================================================

def test_exceedances_cannot_exceed_eligible():

    # Deliberately inconsistent statistical data
    invalid_data = {
        "production_area_id": 6,
        "production_area": "Nordmøre og Sør-Trøndelag",
        "unique_localities": 143,
        "eligible_observations": 100,
        "exceedance_observations": 150,
        "exceedance_percentage": 75.0
    }

    # Pydantic must reject the inconsistent observation counts
    with pytest.raises(
        ValidationError,
        match="Exceedance observations cannot exceed"
    ):
        ProductionAreaRecord(**invalid_data)


# ============================================================
# TEST 9: PERCENTAGE CONSISTENCY
# ============================================================

def test_exceedance_percentage_consistency():

    # Observation counts are valid, but percentage is wrong
    invalid_data = {
        "production_area_id": 6,
        "production_area": "Nordmøre og Sør-Trøndelag",
        "unique_localities": 143,
        "eligible_observations": 100,
        "exceedance_observations": 20,
        "exceedance_percentage": 75.0
    }

    # Pydantic must reject the incorrect percentage
    with pytest.raises(
        ValidationError,
        match="Exceedance percentage does not match"
    ):
        ProductionAreaRecord(**invalid_data)


# ============================================================
# TEST 10: VALID STATISTICAL DATA
# ============================================================

def test_valid_production_area_statistics():

    # CASE A: Valid statistics with a rounded percentage
    valid_data = {
        "production_area_id": 6,
        "production_area": "Nordmøre og Sør-Trøndelag",
        "unique_localities": 143,
        "eligible_observations": 4628,
        "exceedance_observations": 291,
        "exceedance_percentage": 6.29
    }

    record = ProductionAreaRecord(**valid_data)

    assert record.production_area_id == 6
    assert record.eligible_observations == 4628
    assert record.exceedance_observations == 291
    assert record.exceedance_percentage == 6.29

    # CASE B: Zero eligible observations
    #
    # This is synthetic test data, not actual Øst-Finnmark data.
    zero_data = {
        "production_area_id": 13,
        "production_area": "Øst-Finnmark",
        "unique_localities": 0,
        "eligible_observations": 0,
        "exceedance_observations": 0,
        "exceedance_percentage": None
    }

    zero_record = ProductionAreaRecord(**zero_data)

    assert zero_record.eligible_observations == 0
    assert zero_record.exceedance_observations == 0
    assert zero_record.exceedance_percentage is None

# ============================================================
# TEST 11: AVAILABLE REPORTING YEARS API
# ============================================================

def test_available_years(monkeypatch):

    # Simulate the years returned by PostgreSQL
    mock_years = [2023, 2024, 2025]

    # Replace the database function with simulated data
    monkeypatch.setattr(
        "api.main.get_available_years",
        lambda: mock_years
    )

    # Send an HTTP GET request
    response = client.get("/api/v1/available-years")

    # Check HTTP status
    assert response.status_code == 200

    # Convert JSON response to Python dictionary
    data = response.json()

    # Verify response values
    assert data["status"] == "success"
    assert data["total_years"] == 3
    assert data["years"] == [2023, 2024, 2025]
