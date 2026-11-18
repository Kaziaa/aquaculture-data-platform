-- ============================================================
-- AquaInsight — PostgreSQL Data Validation
--
-- Purpose:
-- Validate data integrity after importing fishhealth records.
--
-- Database schema: aquainsight
-- Table: fishhealth_weekly
--
-- All queries are read-only.
-- ============================================================


-- ============================================================
-- CHECK 1: Dataset overview
-- ============================================================

SELECT
    COUNT(*) AS total_observations,
    MIN(year) AS first_year,
    MAX(year) AS last_year,
    COUNT(DISTINCT locality_id) AS unique_localities
FROM aquainsight.fishhealth_weekly;


-- ============================================================
-- CHECK 2: Annual observation counts
-- ============================================================

SELECT
    year,
    COUNT(*) AS total_observations
FROM aquainsight.fishhealth_weekly
GROUP BY year
ORDER BY year;


-- ============================================================
-- CHECK 3: Duplicate observation keys
-- Expected result: zero rows
-- ============================================================

SELECT
    year,
    week,
    locality_id,
    COUNT(*) AS duplicate_count
FROM aquainsight.fishhealth_weekly
GROUP BY
    year,
    week,
    locality_id
HAVING COUNT(*) > 1;


-- ============================================================
-- CHECK 4: Missing primary-key values
-- Expected result: 0
-- ============================================================

SELECT
    COUNT(*) AS missing_primary_keys
FROM aquainsight.fishhealth_weekly
WHERE
    year IS NULL
    OR week IS NULL
    OR locality_id IS NULL;


-- ============================================================
-- CHECK 5: Missing adult female lice measurements
-- ============================================================

SELECT
    COUNT(*) AS total_observations,
    COUNT(*) FILTER (
        WHERE adult_female_lice IS NULL
    ) AS missing_measurements,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE adult_female_lice IS NULL
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS missing_percentage
FROM aquainsight.fishhealth_weekly;


-- ============================================================
-- CHECK 6: Reporting conflicts
-- ============================================================

SELECT
    year,
    COUNT(*) AS reporting_conflicts
FROM aquainsight.fishhealth_weekly
WHERE reporting_conflict IS TRUE
GROUP BY year
ORDER BY year;


-- ============================================================
-- CHECK 7: Annual compliance statistics
-- ============================================================

SELECT
    year,

    COUNT(*) FILTER (
        WHERE calculated_lice_exceedance IS NOT NULL
    ) AS eligible_observations,

    COUNT(*) FILTER (
        WHERE calculated_lice_exceedance IS TRUE
    ) AS lice_exceedances

FROM aquainsight.fishhealth_weekly
GROUP BY year
ORDER BY year;
