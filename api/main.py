# ============================================================
# AquaInsight — REST API
# Day 9 — Task 9.18
#
# Features:
#   1. FastAPI application
#   2. Shared PostgreSQL connection pooling
#   3. Pydantic response validation
#   4. Dynamic reporting-year validation
#   5. Database error handling
# ============================================================

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Path
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Database functions
from src.database import get_engine, get_available_years

# Pydantic response models
from api.schemas import (
    AnnualSummaryResponse,
    ProductionAreaResponse,
)


# ============================================================
# 1. APPLICATION LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage the lifecycle of the shared SQLAlchemy Engine.

    Startup:
        The Engine is created when first needed.

    Shutdown:
        Dispose of the Engine and clear its cache.
    """

    # Application startup
    yield

    # Application shutdown
    if get_engine.cache_info().currsize > 0:

        engine = get_engine()

        engine.dispose()

        get_engine.cache_clear()


# ============================================================
# 2. CREATE FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="AquaInsight API",
    description=(
        "REST API for Norwegian aquaculture data analysis, "
        "including sea-lice statistics and production-area trends."
    ),
    version="1.0.0",
    lifespan=lifespan
)


# ============================================================
# 3. ENDPOINT 1 — API HEALTH CHECK
# ============================================================

@app.get(
    "/api/v1/health",
    tags=["Health"],
    summary="Check API availability"
)
def health_check():
    """
    Check whether the FastAPI application is responding.

    This endpoint does not query PostgreSQL.
    """

    return {
        "status": "ok",
        "service": "AquaInsight"
    }


# ============================================================
# 4. ENDPOINT 2 — DATABASE HEALTH CHECK
# ============================================================

@app.get(
    "/api/v1/database/health",
    tags=["Health"],
    summary="Check PostgreSQL connectivity"
)
def database_health_check():
    """
    Verify that the API can communicate with PostgreSQL.
    """

    try:

        # Retrieve the shared SQLAlchemy Engine
        engine = get_engine()

        # Open a connection from the pool
        with engine.connect() as connection:

            result = connection.execute(
                text(
                    "SELECT current_database(), current_user"
                )
            )

            database, user = result.one()

        return {
            "status": "connected",
            "database": database,
            "user": user
        }

    except (SQLAlchemyError, ValueError) as error:

        print(f"Database health-check error: {error}")

        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable"
        ) from error


# ============================================================
# 5. ENDPOINT 3 — NATIONAL ANNUAL SEA-LICE STATISTICS
# ============================================================

@app.get(
    "/api/v1/annual-summary",
    response_model=AnnualSummaryResponse,
    tags=["Analytics"],
    summary="Retrieve annual sea-lice statistics"
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

        # Retrieve the shared SQLAlchemy Engine
        engine = get_engine()

        # SQL query against our validated analytical view
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

        # Execute the query
        with engine.connect() as connection:

            result = connection.execute(query)

            # Retrieve dictionary-like SQL records
            rows = result.mappings().all()

        # Convert SQL results to Python dictionaries
        data = [dict(row) for row in rows]

        return {
            "status": "success",
            "total_years": len(data),
            "data": data
        }

    except (SQLAlchemyError, ValueError) as error:

        print(f"Annual summary query failed: {error}")

        raise HTTPException(
            status_code=503,
            detail="Annual summary data unavailable"
        ) from error


# ============================================================
# 6. ENDPOINT 4 — PRODUCTION-AREA STATISTICS
# ============================================================

@app.get(
    "/api/v1/production-areas/{year}",
    response_model=ProductionAreaResponse,
    tags=["Analytics"],
    summary="Retrieve production-area sea-lice statistics"
)
def get_production_areas(
    year: int = Path(
        ...,
        description="Reporting year available in PostgreSQL"
    )
):
    """
    Retrieve annual sea-lice statistics for Norwegian
    aquaculture production areas.

    The requested year is validated dynamically against
    the years available in PostgreSQL.

    Returns:
        - Production-area ID
        - Production-area name
        - Number of unique localities
        - Eligible observations
        - Exceedance observations
        - Exceedance percentage

    Results are ordered by exceedance percentage,
    highest first.

    Observations with missing production-area IDs
    are excluded from this geographical ranking.
    """

    try:

        # ----------------------------------------------------
        # STEP 1: RETRIEVE AVAILABLE YEARS
        # ----------------------------------------------------

        years = get_available_years()

        # ----------------------------------------------------
        # STEP 2: VALIDATE REQUESTED YEAR
        # ----------------------------------------------------

        if year not in years:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"No aquaculture data available "
                    f"for year {year}"
                )
            )

        # ----------------------------------------------------
        # STEP 3: RETRIEVE SHARED DATABASE ENGINE
        # ----------------------------------------------------

        engine = get_engine()

        # ----------------------------------------------------
        # STEP 4: DEFINE SQL QUERY
        # ----------------------------------------------------

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
              AND production_area_id IS NOT NULL

            ORDER BY
                exceedance_percentage DESC NULLS LAST
        """)

        # ----------------------------------------------------
        # STEP 5: EXECUTE PARAMETERIZED QUERY
        # ----------------------------------------------------

        with engine.connect() as connection:

            result = connection.execute(
                query,
                {"year": year}
            )

            rows = result.mappings().all()

        # ----------------------------------------------------
        # STEP 6: PREPARE API RESPONSE
        # ----------------------------------------------------

        data = [dict(row) for row in rows]

        return {
            "status": "success",
            "year": year,
            "total_production_areas": len(data),
            "data": data
        }

    except (SQLAlchemyError, ValueError) as error:

        print(f"Production-area query failed: {error}")

        raise HTTPException(
            status_code=503,
            detail="Production-area data unavailable"
        ) from error


# ============================================================
# 7. ENDPOINT 5 — AVAILABLE REPORTING YEARS
# ============================================================

@app.get(
    "/api/v1/available-years",
    tags=["Analytics"],
    summary="Retrieve available reporting years"
)
def available_years():
    """
    Retrieve reporting years available in PostgreSQL.

    Unlike a hardcoded year range, these values
    automatically reflect the database contents.
    """

    try:

        # Query PostgreSQL for available reporting years
        years = get_available_years()

        return {
            "status": "success",
            "total_years": len(years),
            "years": years
        }

    except (SQLAlchemyError, ValueError) as error:

        print(f"Available-years query failed: {error}")

        raise HTTPException(
            status_code=503,
            detail="Available reporting years unavailable"
        ) from error
