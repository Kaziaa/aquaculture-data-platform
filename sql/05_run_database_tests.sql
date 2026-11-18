-- ============================================================
-- AquaInsight — Automated PostgreSQL Test Runner
--
-- Purpose:
-- Recreate a predictable test dataset and validate
-- the analytical SQL views.
--
-- IMPORTANT:
-- Execute only against aquainsight_test.
--
-- This script is designed for execution using psql.
-- ============================================================

\set ON_ERROR_STOP on

\echo ''
\echo '========================================'
\echo 'AquaInsight PostgreSQL Validation'
\echo '========================================'


-- ============================================================
-- STEP 1: VERIFY DATABASE
-- ============================================================

DO $$
BEGIN

    IF current_database() <> 'aquainsight_test' THEN

        RAISE EXCEPTION
            'SAFETY ERROR: Expected aquainsight_test, connected to %',
            current_database();

    END IF;

    RAISE NOTICE
        'PASS: Connected to aquainsight_test';

END $$;


-- ============================================================
-- STEP 2: INITIALIZE DATABASE
-- ============================================================

\echo ''
\echo 'Initializing database structure...'

\i sql/00_init_database.sql


-- ============================================================
-- STEP 3: VERIFY EXISTING TEST RECORDS
-- ============================================================

-- The reset is permitted only when existing records
-- belong to our four known synthetic test keys.

DO $$
BEGIN

    IF EXISTS (
        SELECT 1
        FROM aquainsight.fishhealth_weekly
        WHERE NOT (
            year = 2025
            AND week = 1
            AND locality_id IN (
                900001,
                900002,
                900003,
                900004
            )
        )
    ) THEN

        RAISE EXCEPTION
            'SAFETY ERROR: Unexpected observations in test database';

    END IF;

    RAISE NOTICE
        'PASS: Existing records are restricted to test fixtures';

END $$;


-- ============================================================
-- STEP 4: RESET SYNTHETIC DATA
-- ============================================================

-- This removes records only from the isolated test database,
-- after the database and existing-record checks have passed.

\echo ''
\echo 'Resetting synthetic test observations...'

TRUNCATE TABLE aquainsight.fishhealth_weekly;


-- ============================================================
-- STEP 5: INSERT TEST DATA
-- ============================================================

\echo ''
\echo 'Loading synthetic test data...'

\i sql/03_test_data.sql


-- ============================================================
-- STEP 6: CREATE ANALYTICAL VIEWS
-- ============================================================

\echo ''
\echo 'Creating analytical views...'

\i sql/02_analytical_views.sql


-- ============================================================
-- STEP 7: EXECUTE SQL ASSERTIONS
-- ============================================================

\echo ''
\echo 'Executing analytical validation tests...'

\i sql/04_test_analytical_views.sql


-- ============================================================
-- STEP 8: FINAL RECORD COUNT
-- ============================================================

SELECT
    COUNT(*) AS total_test_observations
FROM aquainsight.fishhealth_weekly;


\echo ''
\echo '========================================'
\echo 'AquaInsight SQL validation completed'
\echo '========================================'
