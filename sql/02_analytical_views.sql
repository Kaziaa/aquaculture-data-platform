-- ============================================================
-- AquaInsight — Analytical PostgreSQL Views
-- ============================================================
--
-- Project:
-- AquaInsight — Norwegian Aquaculture Data Platform
--
-- Purpose:
-- Create reusable PostgreSQL analytical views for
-- Norwegian aquaculture health and sea-lice statistics.
--
-- Source:
-- BarentsWatch Fishhealth API
--
-- Reporting period:
-- 2015–2025
--
-- Source table:
-- aquainsight.fishhealth_weekly
--
-- Analytical views:
--
-- 1. aquainsight.v_annual_lice_summary
--    National annual sea-lice statistics
--
-- 2. aquainsight.v_production_area_annual
--    Annual production-area comparisons
--
-- 3. aquainsight.v_annual_data_quality
--    Annual reporting-status and data-quality statistics
--
-- Requirements:
-- The aquainsight schema and fishhealth_weekly table
-- must already exist and contain the required columns.
--
-- ============================================================


-- ============================================================
-- VIEW 1: NATIONAL ANNUAL SEA-LICE SUMMARY
-- ============================================================
--
-- Purpose:
-- Calculate national aquaculture statistics for each year.
--
-- Metrics:
-- - Total observations
-- - Unique localities
-- - Valid adult female lice measurements
-- - Missing adult female lice measurements
-- - Average adult female lice
-- - Regulatory lice-limit exceedances
-- - Eligible compliance observations
-- - Exceedance percentage
--
-- Important:
-- Exceedance percentage uses eligible compliance
-- observations as its denominator.
--
-- ============================================================

CREATE OR REPLACE VIEW aquainsight.v_annual_lice_summary AS

SELECT
    year,

    COUNT(*) AS total_observations,

    COUNT(DISTINCT locality_id) AS unique_localities,

    COUNT(adult_female_lice) AS valid_lice_measurements,

    COUNT(*) - COUNT(adult_female_lice)
        AS missing_lice_measurements,

    ROUND(
        AVG(adult_female_lice)::numeric,
        3
    ) AS average_adult_female_lice,

    COUNT(*) FILTER (
        WHERE calculated_lice_exceedance = TRUE
    ) AS lice_exceedances,

    COUNT(*) FILTER (
        WHERE calculated_lice_exceedance IS NOT NULL
    ) AS eligible_compliance_observations,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE calculated_lice_exceedance = TRUE
        )
        /
        NULLIF(
            COUNT(*) FILTER (
                WHERE calculated_lice_exceedance IS NOT NULL
            ),
            0
        ),
        2
    ) AS exceedance_percentage

FROM aquainsight.fishhealth_weekly

GROUP BY year;


-- ============================================================
-- VIEW 2: PRODUCTION-AREA ANNUAL STATISTICS
-- ============================================================
--
-- Purpose:
-- Compare Norwegian aquaculture production areas
-- within each reporting year.
--
-- Metrics:
-- - Reporting year
-- - Production-area ID
-- - Production-area name
-- - Total observations
-- - Unique localities
-- - Valid adult female lice measurements
-- - Average adult female lice
-- - Eligible compliance observations
-- - Lice-limit exceedances
-- - Exceedance percentage
--
-- Important:
-- Production-area records with missing geographical
-- identifiers are retained in the analytical view.
--
-- ============================================================

CREATE OR REPLACE VIEW aquainsight.v_production_area_annual AS

SELECT
    year,

    production_area_id,

    production_area,

    COUNT(*) AS total_observations,

    COUNT(DISTINCT locality_id) AS unique_localities,

    COUNT(adult_female_lice) AS valid_lice_measurements,

    ROUND(
        AVG(adult_female_lice)::numeric,
        3
    ) AS average_adult_female_lice,

    COUNT(*) FILTER (
        WHERE calculated_lice_exceedance IS NOT NULL
    ) AS eligible_observations,

    COUNT(*) FILTER (
        WHERE calculated_lice_exceedance = TRUE
    ) AS exceedance_observations,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE calculated_lice_exceedance = TRUE
        )
        /
        NULLIF(
            COUNT(*) FILTER (
                WHERE calculated_lice_exceedance IS NOT NULL
            ),
            0
        ),
        2
    ) AS exceedance_percentage

FROM aquainsight.fishhealth_weekly

GROUP BY
    year,
    production_area_id,
    production_area;


-- ============================================================
-- VIEW 3: ANNUAL DATA-QUALITY SUMMARY
-- ============================================================
--
-- Purpose:
-- Summarize missing sea-lice measurements and
-- reporting-status indicators for each year.
--
-- Metrics:
-- - Total observations
-- - Probably without fish and lice not counted
-- - Not flagged as without fish, lice not counted
-- - Observations with lice counted
-- - Missing adult female lice measurements
-- - Missing measurement percentage
-- - Reporting conflicts
--
-- Important:
--
-- Missing lice measurements do not automatically
-- indicate reporting failures.
--
-- The probably_without_fish column represents
-- a reporting indicator, not confirmed fish absence.
--
-- Reporting conflicts are retained for investigation.
--
-- ============================================================

CREATE OR REPLACE VIEW aquainsight.v_annual_data_quality AS

SELECT
    year,

    COUNT(*) AS total_observations,

    COUNT(*) FILTER (
        WHERE probably_without_fish = TRUE
          AND lice_counted = FALSE
    ) AS probably_without_fish_not_counted,

    COUNT(*) FILTER (
        WHERE probably_without_fish = FALSE
          AND lice_counted = FALSE
    ) AS fish_status_false_not_counted,

    COUNT(*) FILTER (
        WHERE lice_counted = TRUE
    ) AS lice_counted_observations,

    COUNT(*) FILTER (
        WHERE adult_female_lice IS NULL
    ) AS missing_lice_measurements,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE adult_female_lice IS NULL
        )
        /
        NULLIF(
            COUNT(*),
            0
        ),
        2
    ) AS missing_percentage,

    COUNT(*) FILTER (
        WHERE reporting_conflict = TRUE
    ) AS reporting_conflicts

FROM aquainsight.fishhealth_weekly

GROUP BY year;


-- ============================================================
-- END OF AQUAINSIGHT ANALYTICAL VIEWS
-- ============================================================
