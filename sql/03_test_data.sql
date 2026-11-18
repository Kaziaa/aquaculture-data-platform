-- ============================================================
-- AquaInsight — Synthetic PostgreSQL Test Data
--
-- Purpose:
-- Insert controlled synthetic observations for validating
-- AquaInsight's PostgreSQL analytical views.
--
-- IMPORTANT:
-- Execute ONLY against aquainsight_test.
--
-- Features:
-- - Database-name safety check
-- - Four synthetic observations
-- - Composite primary-key conflict handling
-- - Repeatable insertion without duplicate records
--
-- Transaction management:
-- This file intentionally contains no BEGIN or COMMIT.
-- The test runner uses psql --single-transaction.
-- ============================================================


-- ============================================================
-- STEP 1: VERIFY DATABASE NAME
-- ============================================================

DO $$
BEGIN

    IF current_database() <> 'aquainsight_test' THEN

        RAISE EXCEPTION
            'SAFETY ERROR: Synthetic data must only be inserted into aquainsight_test. Connected to: %',
            current_database();

    END IF;

    RAISE NOTICE
        'PASS: Synthetic data insertion permitted in aquainsight_test';

END $$;


-- ============================================================
-- STEP 2: INSERT SYNTHETIC OBSERVATIONS
-- ============================================================

INSERT INTO aquainsight.fishhealth_weekly (

    year,
    week,
    locality_id,
    locality_name,

    adult_female_lice,

    probably_without_fish,
    lice_counted,

    production_area_id,
    production_area,

    calculated_lice_exceedance,
    reporting_conflict

)

VALUES

-- ------------------------------------------------------------
-- Observation A
--
-- Normal sea-lice measurement.
-- Adult female lice: 0.20
-- No threshold exceedance.
-- ------------------------------------------------------------

(
    2025,
    1,
    900001,
    'Test Locality A',

    0.20,

    FALSE,
    TRUE,

    3,
    'Karmøy til Sotra',

    FALSE,
    FALSE
),


-- ------------------------------------------------------------
-- Observation B
--
-- Adult female lice: 0.80
-- Threshold exceedance.
-- ------------------------------------------------------------

(
    2025,
    1,
    900002,
    'Test Locality B',

    0.80,

    FALSE,
    TRUE,

    3,
    'Karmøy til Sotra',

    TRUE,
    FALSE
),


-- ------------------------------------------------------------
-- Observation C
--
-- Probably without fish.
-- Sea lice not counted.
-- Adult female lice measurement missing.
-- Not eligible for compliance calculation.
-- ------------------------------------------------------------

(
    2025,
    1,
    900003,
    'Test Locality C',

    NULL,

    TRUE,
    FALSE,

    3,
    'Karmøy til Sotra',

    NULL,
    FALSE
),


-- ------------------------------------------------------------
-- Observation D
--
-- Adult female lice: 0.30
-- Lice counted.
-- Probably without fish = TRUE.
--
-- This creates a reporting conflict.
-- ------------------------------------------------------------

(
    2025,
    1,
    900004,
    'Test Locality D',

    0.30,

    TRUE,
    TRUE,

    6,
    'Nordmøre og Sør-Trøndelag',

    FALSE,
    TRUE
)


-- ============================================================
-- STEP 3: PREVENT DUPLICATE INSERTIONS
-- ============================================================

ON CONFLICT (year, week, locality_id)
DO NOTHING;


-- ============================================================
-- END OF SYNTHETIC TEST DATA
-- ============================================================
