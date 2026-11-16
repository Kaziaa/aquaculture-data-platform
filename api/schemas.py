# ============================================================
# AquaInsight — Pydantic API Response Schemas
# ============================================================
#
# Project:
# AquaInsight — Norwegian Aquaculture Data Platform
#
# Purpose:
# Validate JSON responses returned by the AquaInsight
# FastAPI backend.
#
# Data source:
# BarentsWatch Fishhealth API
#
# Database:
# PostgreSQL
#
# Reporting period:
# 2015–2025
#
# Schemas:
#
# 1. AnnualSummaryRecord
# 2. AnnualSummaryResponse
# 3. ProductionAreaRecord
# 4. ProductionAreaResponse
# 5. DataQualityRecord
# 6. DataQualityResponse
#
# ============================================================


# ============================================================
# 1. IMPORT LIBRARIES
# ============================================================

from typing import Literal

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)


# ============================================================
# 2. ANNUAL SUMMARY RECORD
# ============================================================

class AnnualSummaryRecord(BaseModel):
    """
    Represents national annual sea-lice statistics.

    Source:
        aquainsight.v_annual_lice_summary

    Each record represents one reporting year.
    """

    year: int = Field(
        ge=2015,
        description="Reporting year",
    )

    total_observations: int = Field(
        ge=0,
        description="Total locality-week observations",
    )

    unique_localities: int = Field(
        ge=0,
        description="Number of distinct localities",
    )

    valid_lice_measurements: int = Field(
        ge=0,
        description="Observations with adult female lice measurements",
    )

    missing_lice_measurements: int = Field(
        ge=0,
        description="Observations without adult female lice measurements",
    )

    average_adult_female_lice: float | None = Field(
        default=None,
        ge=0,
        description="Average adult female lice measurement",
    )

    lice_exceedances: int = Field(
        ge=0,
        description="Observations exceeding the applicable lice threshold",
    )

    eligible_compliance_observations: int = Field(
        ge=0,
        description="Observations eligible for compliance assessment",
    )

    exceedance_percentage: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Percentage of eligible observations exceeding the limit",
    )

    # --------------------------------------------------------
    # Annual summary consistency validation
    # --------------------------------------------------------

    @model_validator(mode="after")
    def validate_annual_counts(self):
        """
        Ensure that annual measurement and compliance
        statistics are internally consistent.
        """

        total = self.total_observations

        # Valid and missing measurements must account
        # for all locality-week observations.
        if (
            self.valid_lice_measurements
            + self.missing_lice_measurements
            != total
        ):
            raise ValueError(
                "Valid and missing measurements must sum "
                "to total observations."
            )

        # Eligible observations cannot exceed total records.
        if self.eligible_compliance_observations > total:
            raise ValueError(
                "Eligible observations cannot exceed "
                "total observations."
            )

        # Exceedances cannot exceed eligible observations.
        if (
            self.lice_exceedances
            > self.eligible_compliance_observations
        ):
            raise ValueError(
                "Exceedances cannot exceed eligible observations."
            )

        # Compliance percentage validation
        eligible = self.eligible_compliance_observations

        if eligible == 0:

            if self.exceedance_percentage is not None:
                raise ValueError(
                    "Exceedance percentage must be None "
                    "when eligible observations are zero."
                )

        else:

            if self.exceedance_percentage is None:
                raise ValueError(
                    "Exceedance percentage is required "
                    "when eligible observations are positive."
                )

            expected_percentage = (
                self.lice_exceedances / eligible
            ) * 100

            if abs(
                self.exceedance_percentage
                - expected_percentage
            ) > 0.0051:
                raise ValueError(
                    "Exceedance percentage does not match "
                    "the reported counts."
                )

        return self


# ============================================================
# 3. ANNUAL SUMMARY RESPONSE
# ============================================================

class AnnualSummaryResponse(BaseModel):
    """
    Response schema for:

        GET /api/v1/annual-summary
    """

    status: Literal["success"]

    total_years: int = Field(
        ge=0,
        description="Number of reporting years returned",
    )

    data: list[AnnualSummaryRecord]


# ============================================================
# 4. PRODUCTION-AREA RECORD
# ============================================================

class ProductionAreaRecord(BaseModel):
    """
    Represents production-area statistics for one year.

    Source:
        aquainsight.v_production_area_annual
    """

    production_area_id: int | None = Field(
        default=None,
        description="Production-area identifier",
    )

    production_area: str | None = Field(
        default=None,
        description="Production-area name",
    )

    unique_localities: int = Field(
        ge=0,
        description="Number of distinct localities",
    )

    eligible_observations: int = Field(
        ge=0,
        description="Observations eligible for compliance assessment",
    )

    exceedance_observations: int = Field(
        ge=0,
        description="Observations exceeding the lice threshold",
    )

    exceedance_percentage: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Percentage of eligible observations exceeding the limit",
    )

    # --------------------------------------------------------
    # Production-area consistency validation
    # --------------------------------------------------------

    @model_validator(mode="after")
    def validate_production_area_counts(self):
        """
        Validate production-area exceedance statistics.
        """

        eligible = self.eligible_observations
        exceedances = self.exceedance_observations

        # Exceedances cannot exceed eligible observations.
        if exceedances > eligible:
            raise ValueError(
                "Exceedance observations cannot exceed "
                "eligible observations."
            )

        # Handle production areas without eligible observations.
        if eligible == 0:

            if self.exceedance_percentage is not None:
                raise ValueError(
                    "Exceedance percentage must be None "
                    "when eligible observations are zero."
                )

        else:

            if self.exceedance_percentage is None:
                raise ValueError(
                    "Exceedance percentage is required "
                    "when eligible observations are positive."
                )

            expected_percentage = (
                exceedances / eligible
            ) * 100

            # PostgreSQL rounds percentages to two decimals.
            if abs(
                self.exceedance_percentage
                - expected_percentage
            ) > 0.0051:
                raise ValueError(
                    "Exceedance percentage does not match "
                    "the reported counts."
                )

        return self


# ============================================================
# 5. PRODUCTION-AREA RESPONSE
# ============================================================

class ProductionAreaResponse(BaseModel):
    """
    Response schema for:

        GET /api/v1/production-areas/{year}
    """

    status: Literal["success"]

    year: int = Field(
        ge=2015,
        description="Selected reporting year",
    )

    total_production_areas: int = Field(
        ge=0,
        description="Number of production-area groups returned",
    )

    data: list[ProductionAreaRecord]


# ============================================================
# 6. DATA-QUALITY RECORD
# Day 10 — Task 10.40
# ============================================================

class DataQualityRecord(BaseModel):
    """
    Represents annual reporting-quality statistics.

    Source:
        aquainsight.v_annual_data_quality

    Metrics include:
        - Total observations
        - Reporting-status categories
        - Observations with lice counted
        - Missing adult female lice measurements
        - Missing percentage
        - Reporting conflicts
    """

    year: int = Field(
        ge=2015,
        description="Reporting year",
    )

    total_observations: int = Field(
        ge=0,
        description="Total locality-week observations",
    )

    probably_without_fish_not_counted: int = Field(
        ge=0,
        description=(
            "Observations probably without fish "
            "where lice were not counted"
        ),
    )

    fish_status_false_not_counted: int = Field(
        ge=0,
        description=(
            "Observations not flagged as without fish "
            "where lice were not counted"
        ),
    )

    lice_counted_observations: int = Field(
        ge=0,
        description="Observations where lice were counted",
    )

    missing_lice_measurements: int = Field(
        ge=0,
        description="Observations missing adult female lice measurements",
    )

    missing_percentage: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Percentage of observations missing lice measurements",
    )

    reporting_conflicts: int = Field(
        ge=0,
        description="Potentially inconsistent reporting-status records",
    )

    # --------------------------------------------------------
    # Data-quality consistency validation
    # --------------------------------------------------------

    @model_validator(mode="after")
    def validate_quality_counts(self):
        """
        Validate annual reporting-quality statistics.

        Rules:

        1. Individual counts cannot exceed total observations.

        2. Reporting categories cannot sum to more
           than total observations.

        3. Missing percentage must agree with the
           underlying measurement counts.

        4. Handle zero-observation years safely.
        """

        total = self.total_observations

        # ====================================================
        # RULE 1: INDIVIDUAL COUNT VALIDATION
        # ====================================================

        if self.missing_lice_measurements > total:
            raise ValueError(
                "Missing measurements cannot exceed total observations."
            )

        if self.lice_counted_observations > total:
            raise ValueError(
                "Lice-counted observations cannot exceed total observations."
            )

        if self.reporting_conflicts > total:
            raise ValueError(
                "Reporting conflicts cannot exceed total observations."
            )

        # ====================================================
        # RULE 2: REPORTING-CATEGORY CONSISTENCY
        # ====================================================

        categorized_observations = (
            self.probably_without_fish_not_counted
            + self.fish_status_false_not_counted
            + self.lice_counted_observations
        )

        if categorized_observations > total:
            raise ValueError(
                "Reporting categories cannot exceed total observations."
            )

        # ====================================================
        # RULE 3: MISSING-PERCENTAGE CONSISTENCY
        # ====================================================

        if total == 0:

            # Percentage is undefined when no observations exist.
            if self.missing_percentage is not None:
                raise ValueError(
                    "Missing percentage must be None when total is zero."
                )

        else:

            # Percentage is required for nonempty reporting years.
            if self.missing_percentage is None:
                raise ValueError(
                    "Missing percentage is required when total is positive."
                )

            # Calculate percentage from the original counts.
            expected_percentage = (
                self.missing_lice_measurements / total
            ) * 100

            # Allow for PostgreSQL rounding to two decimals.
            if abs(
                self.missing_percentage - expected_percentage
            ) > 0.0051:
                raise ValueError(
                    "Missing percentage does not match measurement counts."
                )

        return self


# ============================================================
# 7. DATA-QUALITY RESPONSE
# ============================================================

class DataQualityResponse(BaseModel):
    """
    Response schema for:

        GET /api/v1/data-quality
    """

    status: Literal["success"]

    total_years: int = Field(
        ge=0,
        description="Number of reporting years returned",
    )

    data: list[DataQualityRecord]


# ============================================================
# END OF AQUAINSIGHT PYDANTIC SCHEMAS
# ============================================================
