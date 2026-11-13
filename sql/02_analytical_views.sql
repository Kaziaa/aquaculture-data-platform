-- ============================================================
-- AquaInsight — Analytical PostgreSQL Views
-- Day 9 — Task 9.30
--
-- Purpose:
-- Create reusable analytical views for Norwegian aquaculture
-- sea-lice statistics.
--
-- Source table:
-- aquainsight.fishhealth_weekly
--
-- Views:
-- 1. aquainsight.v_annual_lice_summary
-- 2. aquainsight.v_production_area_annual
--
-- Requirements:
-- PostgreSQL database and source table must already exist.
-- ============================================================


-- ============================================================
-- VIEW 1: NATIONAL ANNUAL SEA-LICE SUMMARY
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