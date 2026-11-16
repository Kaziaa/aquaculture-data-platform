# ============================================================
# AquaInsight — FastAPI Backend
#
# Norwegian Aquaculture Health Analytics
#
# Database: PostgreSQL
# ORM / Database interface: SQLAlchemy
# API Framework: FastAPI
# Validation: Pydantic
#
# API endpoints:
#
# 1. GET /api/v1/health
# 2. GET /api/v1/database/health
# 3. GET /api/v1/annual-summary
# 4. GET /api/v1/production-areas/{year}
# 5. GET /api/v1/available-years
# 6. GET /api/v1/data-quality
#
# ============================================================


# ============================================================
# 1. IMPORTS
# ============================================================

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Path
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.database import (
    get_engine,
    get_available_years,
)

from api.schemas import (
    AnnualSummaryResponse,
    ProductionAreaResponse,
    DataQualityResponse,
)


# ============================================================
# 2. APPLICATION LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown.

    SQLAlchemy creates database connections when needed.

    On shutdown, dispose of the shared Engine's connection
    pool and clear the cached Engine reference.
    """

    yield

    if get_engine.cache_info().currsize > 0:
        engine = get_engine()
        engine.dispose()
        get_engine.cache_clear()


# ============================================================
# 3. FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="AquaInsight API",
    description=(
        "REST API for Norwegian aquaculture health "
        "and sea-lice analytics using BarentsWatch data."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================
# 4. ENDPOINT 1 — API HEALTH
# ============================================================

@app.get(
    "/api/v1/health",
    tags=["Health"],
    summary="Check API health",
)
def health_check():
    """
    Verify that the FastAPI application is responding.

    This endpoint does not query PostgreSQL.
    """

    return {
        "status": "ok",
        "service": "AquaInsight",
    }


# ============================================================
# 5. ENDPOINT 2 — DATABASE HEALTH
# ============================================================

@app.get(
    "/api/v1/database/health",
    tags=["Health"],
    summary="Check PostgreSQL connectivity",
)
def database_health_check():
    """
    Verify that PostgreSQL can execute a simple query.
    """

    try:
        engine = get_engine()

        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "ok",
            "database": "PostgreSQL",
        }

    except (SQLAlchemyError, ValueError) as error:

        print(f"Database health check failed: {error}")

        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable",
        ) from error


# ============================================================
# 6. ENDPOINT 3 — NATIONAL ANNUAL SEA-LICE STATISTICS
# ============================================================

@app.get(
    "/api/v1/annual-summary",
    response_model=AnnualSummaryResponse,
    tags=["Analytics"],
    summary="Retrieve annual sea-lice statistics",
)
def get_annual_summary():
    """
    Retrieve national annual sea-lice statistics.

    PostgreSQL view:
        aquainsight.v_annual_lice_summary

    Returns:
        - Reporting year
        - Total observations
        - Unique localities
        - Valid and missing lice measurements
        - Average adult female lice
        - Number of threshold exceedances
        - Eligible compliance observations
        - Exceedance percentage
    """

    try:

        # Retrieve shared SQLAlchemy Engine
        engine = get_engine()

        # Query the validated analytical view
        query = text("""
            SELECT
                year,
                total_observations,
                unique_localities,
                valid_lice_measurements,
                missing_lice_measurements,
                average_adult_female_lice,
                lice_exceedances,
                eligible_compliance_observations,
                exceedance_percentage

            FROM aquainsight.v_annual_lice_summary

            ORDER BY year
        """)

        # Execute query
        with engine.connect() as connection:

            result = connection.execute(query)

            rows = result.mappings().all()

        # Convert SQLAlchemy rows into dictionaries
        data = [dict(row) for row in rows]

        return {
            "status": "success",
            "total_years": len(data),
            "data": data,
        }

    except (SQLAlchemyError, ValueError) as error:

        print(f"Annual summary query failed: {error}")

        raise HTTPException(
            status_code=503,
            detail="Annual summary data unavailable",
        ) from error


# ============================================================
# 7. ENDPOINT 4 — PRODUCTION-AREA STATISTICS
# ============================================================

@app.get(
    "/api/v1/production-areas/{year}",
    response_model=ProductionAreaResponse,
    tags=["Analytics"],
    summary="Retrieve production-area statistics",
)
def get_production_areas(
    year: int = Path(
        ...,
        description="Reporting year available in PostgreSQL",
    ),
):
    """
    Retrieve production-area sea-lice statistics for
    a selected reporting year.

    PostgreSQL view:
        aquainsight.v_production_area_annual

    The reporting year must exist in PostgreSQL.
    """

    # --------------------------------------------------------
    # 7.1 Validate reporting year
    # --------------------------------------------------------

    try:
        available_years = get_available_years()

    except (SQLAlchemyError, ValueError) as error:

        print(f"Failed to retrieve available years: {error}")

        raise HTTPException(
            status_code=503,
            detail="Reporting years unavailable",
        ) from error

    if year not in available_years:

        raise HTTPException(
            status_code=404,
            detail=f"No aquaculture data available for year {year}",
        )

    # --------------------------------------------------------
    # 7.2 Retrieve production-area statistics
    # --------------------------------------------------------

    try:

        engine = get_engine()

        query = text("""
            SELECT
                production_area_id,
                production_area,
                unique_localities,
                eligible_observations,
                exceedance_observations,
                exceedance_percentage

            FROM aquainsight.v_production_area_annual

            WHERE year = :year

            ORDER BY
                exceedance_percentage DESC NULLS LAST,
                production_area_id
        """)

        with engine.connect() as connection:

            result = connection.execute(
                query,
                {"year": year},
            )

            rows = result.mappings().all()

        data = [dict(row) for row in rows]

        return {
            "status": "success",
            "year": year,
            "total_production_areas": len(data),
            "data": data,
        }

    except (SQLAlchemyError, ValueError) as error:

        print(f"Production-area query failed: {error}")

        raise HTTPException(
            status_code=503,
            detail="Production-area data unavailable",
        ) from error


# ============================================================
# 8. ENDPOINT 5 — AVAILABLE REPORTING YEARS
# ============================================================

@app.get(
    "/api/v1/available-years",
    tags=["Analytics"],
    summary="Retrieve available reporting years",
)
def available_years():
    """
    Return available reporting years from PostgreSQL.

    Streamlit uses these years to populate the
    interactive reporting-year selector.
    """

    try:

        years = get_available_years()

        return {
            "status": "success",
            "total_years": len(years),
            "years": years,
        }

    except (SQLAlchemyError, ValueError) as error:

        print(f"Available-years query failed: {error}")

        raise HTTPException(
            status_code=503,
            detail="Reporting years unavailable",
        ) from error


# ============================================================
# 9. ENDPOINT 6 — ANNUAL DATA QUALITY
# Day 10 — Task 10.33
# ============================================================

@app.get(
    "/api/v1/data-quality",
    response_model=DataQualityResponse,
    tags=["Analytics"],
    summary="Retrieve annual aquaculture data-quality statistics",
)
def get_data_quality():
    """
    Retrieve annual reporting-quality statistics.

    PostgreSQL view:
        aquainsight.v_annual_data_quality

    Returns:
        - Reporting year
        - Total observations
        - Probably without fish, lice not counted
        - Not flagged as without fish, lice not counted
        - Lice-counted observations
        - Missing adult female lice measurements
        - Missing measurement percentage
        - Reporting conflicts

    Important:
        Missing measurements do not automatically
        indicate reporting failures.
    """

    try:

        # ----------------------------------------------------
        # 9.1 Retrieve shared database Engine
        # ----------------------------------------------------

        engine = get_engine()

        # ----------------------------------------------------
        # 9.2 Define SQL query
        # ----------------------------------------------------

        query = text("""
            SELECT
                year,
                total_observations,
                probably_without_fish_not_counted,
                fish_status_false_not_counted,
                lice_counted_observations,
                missing_lice_measurements,
                missing_percentage,
                reporting_conflicts

            FROM aquainsight.v_annual_data_quality

            ORDER BY year
        """)

        # ----------------------------------------------------
        # 9.3 Execute SQL query
        # ----------------------------------------------------

        with engine.connect() as connection:

            result = connection.execute(query)

            rows = result.mappings().all()

        # ----------------------------------------------------
        # 9.4 Convert results into Python dictionaries
        # ----------------------------------------------------

        data = [
            dict(row)
            for row in rows
        ]

        # ----------------------------------------------------
        # 9.5 Return validated JSON response
        # ----------------------------------------------------

        return {
            "status": "success",
            "total_years": len(data),
            "data": data,
        }

    except (SQLAlchemyError, ValueError) as error:

        print(f"Data-quality query failed: {error}")

        raise HTTPException(
            status_code=503,
            detail="Data-quality statistics unavailable",
        ) from error


# ============================================================
# END OF AQUAINSIGHT FASTAPI APPLICATION
# ============================================================
