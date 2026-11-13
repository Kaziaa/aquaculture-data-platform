# ============================================================
# AquaInsight — API Response Schemas
# Day 9 — Task 9.11
# Pydantic Models + Statistical Consistency Validation
# ============================================================

from pydantic import BaseModel, Field, model_validator


# ============================================================
# 1. ANNUAL SUMMARY RECORD
# ============================================================

class AnnualSummaryRecord(BaseModel):
    """
    National aquaculture sea-lice statistics for one year.
    """

    year: int = Field(
        description="Reporting year"
    )

    total_observations: int = Field(
        description="Total locality-week observations"
    )

    unique_localities: int = Field(
        description="Number of distinct aquaculture localities"
    )

    valid_lice_measurements: int = Field(
        description="Observations with reported adult female lice values"
    )

    missing_lice_measurements: int = Field(
        description="Observations without adult female lice values"
    )

    average_adult_female_lice: float | None = Field(
        description="Average reported adult female lice count"
    )

    lice_exceedances: int = Field(
        description=(
            "Number of observations meeting or exceeding "
            "the applicable weekly lice threshold"
        )
    )

    eligible_compliance_observations: int = Field(
        description=(
            "Observations with sufficient data to calculate "
            "threshold exceedance"
        )
    )

    exceedance_percentage: float | None = Field(
        description=(
            "Percentage of eligible observations meeting "
            "or exceeding the threshold"
        )
    )


# ============================================================
# 2. ANNUAL SUMMARY RESPONSE
# ============================================================

class AnnualSummaryResponse(BaseModel):
    """
    API response containing national annual statistics.
    """

    status: str = Field(
        description="API request status"
    )

    total_years: int = Field(
        description="Number of annual records returned"
    )

    data: list[AnnualSummaryRecord] = Field(
        description="Annual aquaculture statistics"
    )


# ============================================================
# 3. PRODUCTION-AREA RECORD
# ============================================================

class ProductionAreaRecord(BaseModel):
    """
    Sea-lice statistics for one production area in one year.

    Validates:
        1. Nonnegative observation counts.
        2. Exceedances cannot exceed eligible observations.
        3. Percentage must match the observation counts.
        4. Zero eligible observations require a null percentage.
    """

    production_area_id: int = Field(
        description="Norwegian aquaculture production-area ID"
    )

    production_area: str = Field(
        description="Name of the Norwegian aquaculture production area"
    )

    unique_localities: int = Field(
        ge=0,
        description="Number of distinct aquaculture localities"
    )

    eligible_observations: int = Field(
        ge=0,
        description=(
            "Number of locality-week observations eligible "
            "for compliance calculation"
        )
    )

    exceedance_observations: int = Field(
        ge=0,
        description=(
            "Number of eligible observations meeting or "
            "exceeding the weekly lice threshold"
        )
    )

    exceedance_percentage: float | None = Field(
        ge=0,
        le=100,
        description=(
            "Percentage of eligible observations meeting "
            "or exceeding the weekly threshold"
        )
    )

    # ========================================================
    # CROSS-FIELD STATISTICAL VALIDATION
    # ========================================================

    @model_validator(mode="after")
    def validate_exceedance_counts(self):
        """
        Validate consistency between:
            - eligible_observations
            - exceedance_observations
            - exceedance_percentage

        PostgreSQL percentages are rounded to two decimals.
        """

        # ----------------------------------------------------
        # RULE 1: Exceedances cannot exceed eligible records
        # ----------------------------------------------------

        if self.exceedance_observations > self.eligible_observations:

            raise ValueError(
                "Exceedance observations cannot exceed "
                "eligible observations"
            )

        # ----------------------------------------------------
        # RULE 2: Handle zero eligible observations
        # ----------------------------------------------------

        if self.eligible_observations == 0:

            if self.exceedance_percentage is not None:

                raise ValueError(
                    "Exceedance percentage must be None "
                    "when eligible observations are zero"
                )

        # ----------------------------------------------------
        # RULE 3: Validate calculated percentage
        # ----------------------------------------------------

        else:

            if self.exceedance_percentage is None:

                raise ValueError(
                    "Exceedance percentage cannot be None "
                    "when eligible observations are greater than zero"
                )

            # Calculate percentage from actual observation counts
            calculated_percentage = (
                self.exceedance_observations
                / self.eligible_observations
                * 100
            )

            # Calculate difference between reported and expected
            difference = abs(
                calculated_percentage
                - self.exceedance_percentage
            )

            # Allow small differences from rounding to two decimals
            tolerance = 0.0051

            if difference > tolerance:

                raise ValueError(
                    "Exceedance percentage does not match "
                    "eligible and exceedance observations"
                )

        # Return the validated record
        return self


# ============================================================
# 4. PRODUCTION-AREA RESPONSE
# ============================================================

class ProductionAreaResponse(BaseModel):
    """
    Complete API response containing production-area statistics.
    """

    status: str = Field(
        description="API request status"
    )

    year: int = Field(
        description="Requested reporting year"
    )

    total_production_areas: int = Field(
        ge=0,
        description="Number of production areas returned"
    )

    data: list[ProductionAreaRecord] = Field(
        description=(
            "Production-area statistics ranked "
            "by exceedance percentage"
        )
    )
